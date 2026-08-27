"""Tests for scripts/settle_db_tables.py.

The failure this guards against: each PAINT update step commits a few hundred million
rows at once (db_caller.py runs a whole .sql file in one transaction and commits at the
end), so autovacuum fires the moment the step returns. The next step then either queues
behind the vacuum's lock, crawls while the vacuum saturates disk I/O, or picks a terrible
plan off stats the vacuum has not caught up on yet. Settling the tables between steps
turns that unpredictable stall into a bounded, visible wait.
"""

import os
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import settle_db_tables as sdt  # noqa: E402


class FakeClock:
    """Monotonic clock that only advances when something sleeps on it."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeDatabase:
    """Stands in for the psycopg2 connection; records what settle() asked it to do.

    polls is a queue of successive running_autovacuums() results - one entry per poll, so a
    test spells out "busy, busy, then clear" as a list. Running past the end reads as clear.
    """

    def __init__(self, present=(), polls=(), version=sdt.MIN_PROGRESS_VIEW_VERSION):
        self.present = set(present)
        self.polls = list(polls)
        self.version = version
        self.poll_count = 0
        self.vacuumed = []

    def server_version_num(self):
        return self.version

    def existing_relations(self, schema, relations):
        return [r for r in relations if r in self.present]

    def running_autovacuums(self, schema, relations):
        running = self.polls[self.poll_count] if self.poll_count < len(self.polls) else []
        self.poll_count += 1
        return [v for v in running if v.relation in relations]

    def vacuum_analyze(self, schema, relation):
        self.vacuumed.append(relation)


def vacuum(relation, wraparound=False):
    return sdt.RunningVacuum(pid=101, relation=relation, phase="scanning heap",
                             wraparound=wraparound)


def settle(db, relations, **kwargs):
    """settle() with a fake clock wired in, so no test actually sleeps."""
    clock = kwargs.pop("clock", FakeClock())
    kwargs.setdefault("poll_interval", 15)
    kwargs.setdefault("timeout", 3600)
    return sdt.settle(db, "panther_upl", list(relations),
                      clock=clock, sleeper=clock.sleep, **kwargs)


### Vacuuming the named relations

def test_settle_vacuum_analyzes_each_named_relation():
    db = FakeDatabase(present=["go_annotation_new", "go_evidence_new"])

    settle(db, ["go_annotation_new", "go_evidence_new"])

    assert db.vacuumed == ["go_annotation_new", "go_evidence_new"]


def test_settle_skips_a_relation_that_does_not_exist():
    """The _new/_old names shift as the run progresses; a missing one must not be fatal."""
    db = FakeDatabase(present=["go_evidence_new"])

    settle(db, ["go_annotation_new", "go_evidence_new"])

    assert db.vacuumed == ["go_evidence_new"]


def test_settle_names_the_missing_relation_in_its_warning(capsys):
    db = FakeDatabase(present=["go_evidence_new"])

    settle(db, ["go_annotation_new", "go_evidence_new"])

    assert "go_annotation_new" in capsys.readouterr().out


def test_settle_vacuums_nothing_when_no_named_relation_exists():
    db = FakeDatabase(present=[])

    settle(db, ["go_annotation_new"])

    assert db.vacuumed == []


### Waiting for autovacuum to drain

def test_settle_waits_while_an_autovacuum_worker_runs_on_a_named_relation():
    db = FakeDatabase(present=["go_annotation_new"],
                      polls=[[vacuum("go_annotation_new")],
                             [vacuum("go_annotation_new")],
                             []])
    clock = FakeClock()

    settle(db, ["go_annotation_new"], clock=clock, poll_interval=15)

    assert clock.now == 30


def test_settle_ignores_autovacuum_on_a_relation_it_was_not_asked_about():
    db = FakeDatabase(present=["go_annotation_new"],
                      polls=[[vacuum("some_unrelated_table")]])
    clock = FakeClock()

    settle(db, ["go_annotation_new"], clock=clock)

    assert clock.now == 0


def test_settle_vacuums_only_after_the_wait_clears():
    """Vacuuming while a worker is still on the table is the stall we are avoiding."""
    vacuumed_at_poll = []
    db = FakeDatabase(present=["go_annotation_new"],
                      polls=[[vacuum("go_annotation_new")], []])
    real_vacuum = db.vacuum_analyze
    db.vacuum_analyze = lambda s, r: (vacuumed_at_poll.append(db.poll_count),
                                      real_vacuum(s, r))

    settle(db, ["go_annotation_new"])

    assert vacuumed_at_poll == [2]


def test_settle_raises_when_the_wait_exceeds_the_timeout():
    db = FakeDatabase(present=["go_annotation_new"],
                      polls=[[vacuum("go_annotation_new")]] * 100)

    with pytest.raises(sdt.SettleTimeout):
        settle(db, ["go_annotation_new"], poll_interval=15, timeout=60)


def test_settle_does_not_vacuum_after_a_timeout():
    db = FakeDatabase(present=["go_annotation_new"],
                      polls=[[vacuum("go_annotation_new")]] * 100)

    with pytest.raises(sdt.SettleTimeout):
        settle(db, ["go_annotation_new"], poll_interval=15, timeout=60)

    assert db.vacuumed == []


def test_settle_flags_an_antiwraparound_vacuum(capsys):
    """Ordinary autovacuum yields to a conflicting lock; a wraparound vacuum does not,
    so it is the one case that can genuinely stall for hours."""
    db = FakeDatabase(present=["go_annotation_new"],
                      polls=[[vacuum("go_annotation_new", wraparound=True)], []])

    settle(db, ["go_annotation_new"])

    assert "wraparound" in capsys.readouterr().out.lower()


### Server version compatibility

def test_running_vacuum_query_uses_the_progress_view_on_9_6_and_up():
    assert "pg_stat_progress_vacuum" in sdt.running_vacuum_query(90600)


def test_running_vacuum_query_falls_back_to_stat_activity_below_9_6():
    query = sdt.running_vacuum_query(90500)

    assert "pg_stat_progress_vacuum" not in query
    assert "pg_stat_activity" in query


### Dry run

def test_dry_run_neither_polls_nor_vacuums():
    db = FakeDatabase(present=["go_annotation_new"],
                      polls=[[vacuum("go_annotation_new")]])

    settle(db, ["go_annotation_new"], dry_run=True)

    assert (db.poll_count, db.vacuumed) == (0, [])
