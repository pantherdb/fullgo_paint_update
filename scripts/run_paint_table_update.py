"""Run the whole "Updating PAINT tables" block as one command.

    make update_paint_tables

README.md used to document this as twelve make calls to retype by hand once a month. A
skipped one is not noticed until GAF generation produces wrong output hours later, so the
list lives here now and README points at it.

Between the write-heavy steps this interleaves scripts/settle_db_tables.py, which waits
for autovacuum to drain off the tables that step just rewrote and then VACUUM (ANALYZE)s
them. db_caller.py commits each .sql file as a single transaction, so autovacuum starts
the instant a step returns and the next step pays for it in lock waits, I/O contention or
plans built on stale stats. See settle_db_tables.py for the full reasoning.

switch_table_names_go_only is the point of no return - it renames the _new tables over the
live ones. Everything before it only touches _new tables, so a failed run can be resumed.
The switch is therefore gated: it asks first, and an unattended run that cannot ask stops
in front of it rather than flipping the live tables on its own.

    make update_paint_tables                              # ask before the switch
    make CONFIRM_SWITCH=1 update_paint_tables             # unattended, switch included
    make DRY_RUN=1 update_paint_tables                    # print the plan, run nothing
    make START_AT=update_paint_go_evidence update_paint_tables    # resume after a failure
    make STOP_AFTER=gen_iba_gaf_yamls update_paint_tables         # stop before the switch
"""

import argparse
import os
import subprocess
import sys
import time
from collections import namedtuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_SCHEMA = "panther_upl"
SETTLE_SCRIPT = "scripts/settle_db_tables.py"

# target  : the make recipe to run
# settle  : relations to settle once it finishes, named as they exist *after* the step
# affects : live table names the step's _new tables shadow, for reset_paint_table.sh
# gate    : ask before running this one - it is not reversible
Step = namedtuple("Step", ["target", "settle", "affects", "gate"])


def step(target, settle=(), affects=(), gate=False):
    return Step(target, tuple(settle), tuple(affects), gate)


STEPS = (
    step("load_raw_go_to_paint",
         settle=("goanno_wf", "goobo_extract", "goobo_parent_child")),
    # go_classification.sql DROPs and CREATEs go_classification_descendants, and a fresh
    # materialized view carries no stats at all until something analyzes it.
    step("update_paint_go_classification",
         settle=("go_classification_new", "go_classification_relationship_new",
                 "fullgo_version_new", "go_classification_descendants"),
         affects=("go_classification", "go_classification_relationship",
                  "fullgo_version")),
    step("update_paint_go_annotation",
         settle=("go_annotation_new",),
         affects=("go_annotation",)),
    step("update_paint_go_evidence",
         settle=("go_evidence_new",),
         affects=("go_evidence",)),
    # go_annotation_qualifier.sql rebuilds the goanno_w_qualifier matview and updates
    # go_evidence_new on the way through.
    step("update_paint_go_annot_qualifier",
         settle=("go_annotation_qualifier_new", "go_evidence_qualifier_new",
                 "goanno_w_qualifier", "go_evidence_new"),
         affects=("go_annotation_qualifier", "go_evidence_qualifier")),
    step("switch_evidence_to_pmid", settle=("go_evidence_new",)),
    step("delete_incorrect_go_annot_qualifiers", settle=("go_annotation_qualifier_new",)),
    # File generation, not DB writes: builds the pre-update IBA GAFs to diff against.
    step("setup_preupdate_data"),
    step("gen_iba_gaf_yamls"),
    step("switch_table_names_go_only", gate=True),
    step("regenerate_go_aggregate_view"),
    step("regenerate_paint_aggregate_view"),
)

# Checked before the first step so a missing file costs seconds rather than hours.
#   config.yaml            every db_caller.py call needs the credentials
#   profile.txt            check-profile, and the go_release_date fullgo_version.sql wants
#   complex_terms.tsv      setup_preupdate_data prerequisite and symlink source
PREREQUISITE_FILES = (
    ("{repo_root}/config/config.yaml", "DB credentials for db_caller.py"),
    ("{base_path}/profile.txt", "GO release metadata (make make_profile)"),
    ("{base_path}/resources/complex_terms.tsv", "setup_preupdate_data prerequisite"),
)


class UnknownStep(Exception):
    """START_AT or STOP_AFTER named something that is not in the step list."""


def step_names(steps):
    return [s.target for s in steps]


def select_steps(steps, start_at=None, stop_after=None):
    """Narrow the list to a resumable range. Skipping a step skips its settle with it."""
    names = step_names(steps)
    for label, name in (("START_AT", start_at), ("STOP_AFTER", stop_after)):
        if name and name not in names:
            raise UnknownStep("{}={} is not a step. Steps are: {}".format(
                label, name, ", ".join(names)))
    first = names.index(start_at) if start_at else 0
    last = names.index(stop_after) if stop_after else len(names) - 1
    if last < first:
        raise UnknownStep("STOP_AFTER={} comes before START_AT={}".format(
            stop_after, start_at))
    return list(steps[first:last + 1])


def missing_prerequisites(base_path, repo_root=REPO_ROOT, exists=os.path.exists):
    missing = []
    for template, why in PREREQUISITE_FILES:
        path = template.format(repo_root=repo_root, base_path=base_path)
        if not exists(path):
            missing.append("{} - {}".format(path, why))
    return missing


def make_command(base_path, target):
    return ["make", "BASE_PATH={}".format(base_path), target]


def settle_command(schema, relations, timeout=None):
    command = ["python3", SETTLE_SCRIPT, "--schema", schema]
    if timeout:
        command += ["--timeout", "{:g}".format(float(timeout))]
    return command + list(relations)


def resume_command(base_path, target):
    return "make BASE_PATH={} START_AT={} update_paint_tables".format(base_path, target)


def print_plan(steps, base_path, schema, settle_timeout=None, out=print):
    out("[plan] {} steps against BASE_PATH={}".format(len(steps), base_path))
    for number, current in enumerate(steps, start=1):
        if current.gate:
            out("       ---- confirmation gate: point of no return "
                "(CONFIRM_SWITCH=1 to auto-approve) ----")
        out("  {:>2}. {}".format(number, " ".join(make_command(base_path, current.target))))
        if current.settle:
            out("      {}".format(" ".join(
                settle_command(schema, current.settle, settle_timeout))))


def format_duration(seconds):
    return "{:d}m{:02d}s".format(int(seconds) // 60, int(seconds) % 60)


def print_summary(timings, out=print):
    if not timings:
        return
    out("[done] step timings:")
    for label, seconds in timings:
        out("  {:>8}  {}".format(format_duration(seconds), label))
    out("  {:>8}  TOTAL".format(format_duration(sum(s for _, s in timings))))


def tty_confirmer(current):
    """Ask on the terminal, not stdin - stdin may be a pipe while a tty still exists."""
    with open("/dev/tty") as terminal:
        print("Run {}? This renames the _new tables over the live ones. [y/N] ".format(
            current.target), end="", flush=True)
        return terminal.readline().strip().lower() in ("y", "yes")


def run(steps, runner, base_path=None, repo_root=REPO_ROOT, schema=DEFAULT_SCHEMA,
        settle_timeout=None, confirmer=None, confirm_switch=False, dry_run=False,
        preflight=True, out=print, clock=time.monotonic):
    """Execute `steps` through `runner`. Returns a process exit code."""
    steps = list(steps)
    if dry_run:
        print_plan(steps, base_path, schema, settle_timeout, out=out)
        return 0

    if preflight:
        missing = missing_prerequisites(base_path, repo_root=repo_root)
        if missing:
            out("[preflight] cannot start, missing:")
            for item in missing:
                out("  {}".format(item))
            return 1

    affected = []
    timings = []

    def fail(label, resume_at, code):
        out("")
        out("[fail] {} exited {}".format(label, code))
        out("[fail] AFFECTED_TABLES={}".format(" ".join(affected)))
        if resume_at:
            out("[fail] resume with: {}".format(resume_command(base_path, resume_at)))
        print_summary(timings, out=out)
        return code

    for position, current in enumerate(steps):
        if current.gate:
            runner(make_command(base_path, "paint_go_table_counts"))
            if not confirm_switch:
                if confirmer is None:
                    out("")
                    out("[gate] stopping in front of {} - nothing here can confirm it "
                        "and it is not reversible.".format(current.target))
                    out("[gate] review the counts above, then: {}".format(
                        resume_command(base_path, current.target)))
                    out("[gate] or re-run unattended with CONFIRM_SWITCH=1.")
                    print_summary(timings, out=out)
                    return 0
                if not confirmer(current):
                    out("[gate] declined - stopping before {}.".format(current.target))
                    out("[gate] resume with: {}".format(
                        resume_command(base_path, current.target)))
                    print_summary(timings, out=out)
                    return 0

        started = clock()
        code = runner(make_command(base_path, current.target))
        timings.append((current.target, clock() - started))
        if code != 0:
            return fail("step {}".format(current.target), current.target, code)
        affected.extend(current.affects)

        if current.settle:
            started = clock()
            code = runner(settle_command(schema, current.settle, settle_timeout))
            timings.append(("settle {}".format(current.target), clock() - started))
            if code != 0:
                # The step itself committed, so resuming must not re-run it: its
                # ALTER TABLE ... _old RENAME TO _new has no _old table left to rename.
                following = steps[position + 1].target if position + 1 < len(steps) else None
                return fail("settle after {}".format(current.target), following, code)

    out("")
    out("[done] {} of {} steps".format(len(steps), len(STEPS)))
    print_summary(timings, out=out)
    return 0


class MakeRunner:
    """Runs a command, streaming its output to the terminal and to BASE_PATH/log.txt.

    Replaces the `make <recipe> | tee -a log.txt` the pipeline is documented with, without
    the pipe hiding make's exit code.
    """

    def __init__(self, log_path=None, cwd=REPO_ROOT, out=sys.stdout):
        self.log_path = log_path
        self.cwd = cwd
        self.out = out

    def __call__(self, cmd):
        log = open(self.log_path, "a") if self.log_path else None
        try:
            # The banner goes to the log too: output with no step boundaries is
            # unreadable when someone comes back to log.txt weeks later.
            self._write("\n$ {}\n".format(" ".join(cmd)), log)
            process = subprocess.Popen(cmd, cwd=self.cwd, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in process.stdout:
                self._write(line, log)
            return process.wait()
        finally:
            if log:
                log.close()

    def _write(self, text, log):
        self.out.write(text)
        self.out.flush()
        if log:
            log.write(text)


def env_flag(name):
    """Makefile passes these through as empty-or-set, matching DRY_RUN elsewhere."""
    return bool(os.environ.get(name, "").strip())


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("-b", "--base_path", default=os.environ.get("BASE_PATH"),
                        help="release working directory (default: $BASE_PATH)")
    parser.add_argument("-s", "--schema", default=DEFAULT_SCHEMA)
    parser.add_argument("--start_at", default=os.environ.get("START_AT") or None,
                        help="resume from this step, skipping everything before it")
    parser.add_argument("--stop_after", default=os.environ.get("STOP_AFTER") or None,
                        help="stop once this step and its settle have finished")
    parser.add_argument("--settle_timeout", type=float,
                        default=float(os.environ["SETTLE_TIMEOUT"])
                        if os.environ.get("SETTLE_TIMEOUT", "").strip() else None,
                        help="seconds each settle waits for autovacuum before giving up")
    parser.add_argument("--confirm_switch", action="store_true",
                        default=env_flag("CONFIRM_SWITCH"),
                        help="run switch_table_names_go_only without asking")
    parser.add_argument("--dry_run", action="store_true", default=env_flag("DRY_RUN"),
                        help="print the plan without running anything")
    parser.add_argument("--list", action="store_true", help="print the step names and exit")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.list:
        print("\n".join(step_names(STEPS)))
        return 0
    if not args.base_path:
        print("ERROR: no BASE_PATH set (pass --base_path or run via make).")
        return 1

    try:
        steps = select_steps(STEPS, start_at=args.start_at, stop_after=args.stop_after)
    except UnknownStep as unknown:
        print("ERROR: {}".format(unknown))
        return 1

    runner = MakeRunner(log_path=os.path.join(args.base_path, "log.txt")
                        if os.path.isdir(args.base_path) else None)
    return run(steps, runner, base_path=args.base_path, schema=args.schema,
               settle_timeout=args.settle_timeout,
               confirmer=tty_confirmer if sys.stdin.isatty() else None,
               confirm_switch=args.confirm_switch, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
