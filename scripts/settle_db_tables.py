"""Wait for autovacuum to drain off a set of tables, then VACUUM (ANALYZE) them.

Run between the write-heavy PAINT update steps (see scripts/run_paint_table_update.py).
Each of those steps goes through db_caller.py, which executes a whole .sql file on one
non-autocommit connection and commits at the very end - so a few hundred million rows
land in a single commit and autovacuum starts the instant the step returns. Whatever runs
next then pays for it in one of three ways:

    lock      the next step's ALTER TABLE ... RENAME wants ACCESS EXCLUSIVE and queues
              behind the worker
    I/O       the next step runs but crawls while the worker saturates the disk
    bad plan  the next step plans against stats the worker has not refreshed yet. The
              materialized views are the worst case here: go_classification.sql and
              go_annotation_qualifier.sql DROP and CREATE go_classification_descendants
              and goanno_w_qualifier, and a fresh matview has no stats at all.

Settling fixes all three: the wait clears the lock and the I/O, the ANALYZE fixes the
stats, and doing it explicitly resets the dead-tuple counters so autovacuum has no reason
to fire again in the middle of the next step. The cost is the same vacuum either way -
this just makes it synchronous and visible instead of a surprise stall.

This cannot be a .sql file run through db_caller.py: VACUUM cannot run inside a
transaction block, and DBCaller never sets autocommit. It reuses DBCallerConfig for
credentials and opens its own autocommit connection.

    python3 scripts/settle_db_tables.py go_annotation_new go_evidence_new
"""

import argparse
import sys
import time
from collections import namedtuple

MIN_PROGRESS_VIEW_VERSION = 90600  # pg_stat_progress_vacuum landed in 9.6
DEFAULT_SCHEMA = "panther_upl"
DEFAULT_POLL_INTERVAL = 15
DEFAULT_TIMEOUT = 3600

# Relation kinds worth vacuuming: ordinary table, materialized view, partitioned table.
VACUUMABLE_RELKINDS = ("r", "m", "p")

RunningVacuum = namedtuple("RunningVacuum", ["pid", "relation", "phase", "wraparound"])
VacuumResult = namedtuple("VacuumResult", ["relation", "seconds"])

# Both queries take exactly one parameter, the schema name, and both return
# (pid, relation, phase, wraparound). Relation is the bare relname in both.
PROGRESS_VIEW_QUERY = """
SELECT a.pid,
       c.relname,
       p.phase,
       (a.query LIKE '%%to prevent wraparound%%') AS wraparound
FROM pg_stat_progress_vacuum p
JOIN pg_stat_activity a ON a.pid = p.pid
JOIN pg_class c ON c.oid = p.relid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = %s
"""

# Pre-9.6 has no progress view, so the relation has to come out of the query text
# ("autovacuum: VACUUM ANALYZE panther_upl.go_annotation_new (to prevent wraparound)").
STAT_ACTIVITY_QUERY = r"""
SELECT pid,
       substring(query from '\.([a-zA-Z0-9_]+)') AS relname,
       'running' AS phase,
       (query LIKE '%%to prevent wraparound%%') AS wraparound
FROM pg_stat_activity
WHERE query LIKE 'autovacuum: %%'
  AND position(%s || '.' in query) > 0
"""


class SettleTimeout(Exception):
    """Autovacuum was still running on the tables when the timeout ran out."""


def running_vacuum_query(server_version_num):
    """Progress view where available, query-text scraping on older servers.

    The progress view is the better source: it also catches a manual VACUUM, which stalls
    the next step exactly as an autovacuum worker would.
    """
    if server_version_num >= MIN_PROGRESS_VIEW_VERSION:
        return PROGRESS_VIEW_QUERY
    return STAT_ACTIVITY_QUERY


class PsycopgDatabase:
    """The real database, on an autocommit connection so VACUUM is legal."""

    def __init__(self, config=None):
        import psycopg2  # imported here so --dry_run needs no driver and no server

        from pthr_db_caller.db_caller import DBCallerConfig

        self.config = config or DBCallerConfig()
        self.connection = psycopg2.connect(
            "dbname={} user={} host={} password={}".format(
                self.config.dbname, self.config.username,
                self.config.host, self.config.pword))
        self.connection.autocommit = True
        self._version = None

    def _rows(self, query, params):
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def server_version_num(self):
        if self._version is None:
            self._version = self.connection.server_version
        return self._version

    def existing_relations(self, schema, relations):
        """Names that actually exist right now, in the caller's order.

        The _new/_old names shift as the update progresses, so a name that is absent at
        this moment is expected rather than an error.
        """
        # relname is `name` and relkind is `"char"`; psycopg2 renders a Python list as an
        # ARRAY[] of unknown literals that PostgreSQL resolves to text[], so cast both
        # sides to text rather than rely on which implicit casts happen to exist.
        rows = self._rows(
            "SELECT c.relname FROM pg_class c"
            " JOIN pg_namespace n ON n.oid = c.relnamespace"
            " WHERE n.nspname = %s AND c.relname::text = ANY(%s)"
            " AND c.relkind::text = ANY(%s)",
            (schema, list(relations), list(VACUUMABLE_RELKINDS)))
        found = {r[0] for r in rows}
        return [r for r in relations if r in found]

    def running_autovacuums(self, schema, relations):
        rows = self._rows(running_vacuum_query(self.server_version_num()), (schema,))
        wanted = set(relations)
        return [RunningVacuum(*row) for row in rows if row[1] in wanted]

    def vacuum_analyze(self, schema, relation):
        from psycopg2 import sql

        with self.connection.cursor() as cursor:
            cursor.execute(sql.SQL("VACUUM (ANALYZE) {}").format(
                sql.Identifier(schema, relation)))


def describe(running):
    text = "  [settle] pid {} is vacuuming {} ({})".format(
        running.pid, running.relation, running.phase)
    if running.wraparound:
        # Ordinary autovacuum is auto-cancelled when it blocks a lock request, so it
        # usually clears itself. A wraparound vacuum is not, and can hold for hours.
        text += " to prevent wraparound - this one will NOT yield, expect a long wait"
    return text


def wait_for_autovacuum(db, schema, relations, poll_interval, timeout,
                        clock=time.monotonic, sleeper=time.sleep, out=print):
    """Poll until nothing is vacuuming any of `relations`. Returns seconds waited."""
    started = clock()
    announced = set()
    while True:
        running = db.running_autovacuums(schema, relations)
        if not running:
            return clock() - started
        for vacuum in running:
            if vacuum.pid not in announced:
                announced.add(vacuum.pid)
                out(describe(vacuum))
        waited = clock() - started
        if waited >= timeout:
            raise SettleTimeout(
                "still vacuuming {} after {:.0f}s: {}".format(
                    schema, waited, ", ".join(sorted(v.relation for v in running))))
        sleeper(poll_interval)


def settle(db, schema, relations, poll_interval=DEFAULT_POLL_INTERVAL,
           timeout=DEFAULT_TIMEOUT, clock=time.monotonic, sleeper=time.sleep,
           dry_run=False, out=print):
    """Wait out any vacuum on `relations`, then VACUUM (ANALYZE) the ones that exist."""
    if dry_run:
        out("[settle] dry run - would settle {}.{{{}}}".format(schema, ",".join(relations)))
        return []

    present = db.existing_relations(schema, relations)
    missing = [r for r in relations if r not in present]
    if missing:
        out("[settle] not present, skipping: {}".format(", ".join(missing)))
    if not present:
        out("[settle] nothing to settle in {}".format(schema))
        return []

    waited = wait_for_autovacuum(db, schema, present, poll_interval, timeout,
                                 clock=clock, sleeper=sleeper, out=out)
    if waited:
        out("[settle] autovacuum cleared after {:.0f}s".format(waited))

    results = []
    for relation in present:
        started = clock()
        db.vacuum_analyze(schema, relation)
        results.append(VacuumResult(relation, clock() - started))
        out("[settle] VACUUM (ANALYZE) {}.{} - {:.0f}s".format(
            schema, relation, results[-1].seconds))
    return results


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("relations", nargs="+",
                        help="table or materialized view names to settle")
    parser.add_argument("-s", "--schema", default=DEFAULT_SCHEMA)
    parser.add_argument("-i", "--poll_interval", type=float, default=DEFAULT_POLL_INTERVAL,
                        help="seconds between autovacuum checks (default {})".format(
                            DEFAULT_POLL_INTERVAL))
    parser.add_argument("-t", "--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help="give up waiting after this many seconds (default {})".format(
                            DEFAULT_TIMEOUT))
    parser.add_argument("--dry_run", action="store_true",
                        help="print what would be settled without connecting to the DB")
    parser.add_argument("--no_fail", action="store_true",
                        help="warn instead of exiting non-zero when the wait times out")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    db = None if args.dry_run else PsycopgDatabase()
    try:
        settle(db, args.schema, args.relations, poll_interval=args.poll_interval,
               timeout=args.timeout, dry_run=args.dry_run)
    except SettleTimeout as timeout:
        print("[settle] TIMEOUT: {}".format(timeout))
        if not args.no_fail:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
