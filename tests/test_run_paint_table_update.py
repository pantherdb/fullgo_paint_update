"""Tests for scripts/run_paint_table_update.py.

Two failures this guards against. The first is forgetting a step: "Updating PAINT tables"
was a twelve-line block of make calls in README.md that an operator retyped by hand once a
month, and a skipped step is not noticed until GAF generation produces wrong output hours
later. The second is the autovacuum stall - every write-heavy step needs a settle after it
(see settle_db_tables.py), and a settle is exactly the kind of thing hand-running omits.

switch_table_names_go_only is the point of no return: it renames the _new tables over the
live ones. Everything before it only touches _new tables and can be re-run.
"""

import io
import os
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import run_paint_table_update as rptu  # noqa: E402

# The block README.md documented, in order. Kept spelled out rather than derived from
# STEPS so that dropping a step from STEPS fails a test instead of quietly agreeing.
README_STEPS = [
    "load_raw_go_to_paint",
    "update_paint_go_classification",
    "update_paint_go_annotation",
    "update_paint_go_evidence",
    "update_paint_go_annot_qualifier",
    "switch_evidence_to_pmid",
    "delete_incorrect_go_annot_qualifiers",
    "setup_preupdate_data",
    "gen_iba_gaf_yamls",
    "switch_table_names_go_only",
    "regenerate_go_aggregate_view",
    "regenerate_paint_aggregate_view",
]


class FakeRunner:
    """Records argv instead of running it. fail_on names the step that returns non-zero."""

    def __init__(self, fail_on=None):
        self.commands = []
        self.fail_on = fail_on

    def __call__(self, cmd):
        self.commands.append(cmd)
        return 1 if self.fail_on and self.fail_on in cmd else 0

    def joined(self):
        return [" ".join(c) for c in self.commands]

    def make_targets(self):
        return [c[-1] for c in self.commands if c[0] == "make"]

    def settles(self):
        return [c for c in self.commands
                if any("settle_db_tables.py" in part for part in c)]

    def settle_relations(self):
        return [c[c.index("--schema") + 2:] for c in self.settles()]


def run(runner, steps=None, **kwargs):
    kwargs.setdefault("base_path", "2026-08-18_fullgo")
    kwargs.setdefault("preflight", False)
    return rptu.run(steps if steps is not None else rptu.STEPS, runner, **kwargs)


### The step list

def test_steps_are_exactly_the_readme_block_in_order():
    assert [s.target for s in rptu.STEPS] == README_STEPS


def test_every_step_that_writes_go_tables_settles_afterward():
    write_steps = [s for s in rptu.STEPS if s.target.startswith(("load_raw", "update_paint",
                                                                "switch_evidence",
                                                                "delete_incorrect"))]

    assert [s.target for s in write_steps if not s.settle] == []


def test_the_annotation_step_settles_the_table_it_rebuilds():
    step = next(s for s in rptu.STEPS if s.target == "update_paint_go_annotation")

    assert step.settle == ("go_annotation_new",)


def test_the_classification_step_settles_its_materialized_view():
    """go_classification.sql DROPs and CREATEs it, so it has no stats until analyzed."""
    step = next(s for s in rptu.STEPS if s.target == "update_paint_go_classification")

    assert "go_classification_descendants" in step.settle


def test_only_the_table_switch_is_gated():
    assert [s.target for s in rptu.STEPS if s.gate] == ["switch_table_names_go_only"]


### Choosing which steps to run

def test_start_at_skips_the_earlier_steps():
    selected = rptu.select_steps(rptu.STEPS, start_at="update_paint_go_evidence")

    assert [s.target for s in selected] == README_STEPS[3:]


def test_stop_after_drops_the_later_steps():
    selected = rptu.select_steps(rptu.STEPS, stop_after="update_paint_go_evidence")

    assert [s.target for s in selected] == README_STEPS[:4]


def test_start_at_and_stop_after_select_a_middle_range():
    selected = rptu.select_steps(rptu.STEPS, start_at="update_paint_go_annotation",
                                 stop_after="update_paint_go_evidence")

    assert [s.target for s in selected] == README_STEPS[2:4]


def test_start_at_an_unknown_step_raises():
    with pytest.raises(rptu.UnknownStep):
        rptu.select_steps(rptu.STEPS, start_at="update_paint_go_annotations")


def test_unknown_step_error_lists_the_valid_names():
    with pytest.raises(rptu.UnknownStep, match="update_paint_go_annotation"):
        rptu.select_steps(rptu.STEPS, start_at="nonsense")


def test_stop_after_before_start_at_raises():
    with pytest.raises(rptu.UnknownStep):
        rptu.select_steps(rptu.STEPS, start_at="update_paint_go_evidence",
                          stop_after="update_paint_go_annotation")


def test_skipping_a_step_skips_its_settle():
    runner = FakeRunner()

    run(runner, rptu.select_steps(rptu.STEPS, stop_after="load_raw_go_to_paint"))

    assert runner.settle_relations() == [["goanno_wf", "goobo_extract",
                                          "goobo_parent_child"]]


### Running

def test_run_makes_every_step_in_order():
    runner = FakeRunner()

    run(runner, confirm_switch=True)

    expected = list(README_STEPS)
    expected.insert(expected.index("switch_table_names_go_only"), "paint_go_table_counts")
    assert runner.make_targets() == expected


def test_run_settles_immediately_after_the_step_that_dirtied_the_tables():
    runner = FakeRunner()

    run(runner, rptu.select_steps(rptu.STEPS, stop_after="update_paint_go_annotation"))

    assert runner.joined()[-2:] == [
        "make BASE_PATH=2026-08-18_fullgo update_paint_go_annotation",
        "python3 scripts/settle_db_tables.py --schema panther_upl go_annotation_new",
    ]


def test_run_passes_the_base_path_to_every_make_call():
    runner = FakeRunner()

    run(runner, base_path="2026-09-01_fullgo", confirm_switch=True)

    assert all("BASE_PATH=2026-09-01_fullgo" in c for c in runner.commands
               if c[0] == "make")


def test_run_stops_at_the_first_failing_step():
    runner = FakeRunner(fail_on="update_paint_go_annotation")

    run(runner)

    assert "update_paint_go_evidence" not in runner.make_targets()


def test_run_does_not_settle_after_a_failing_step():
    runner = FakeRunner(fail_on="update_paint_go_annotation")

    run(runner)

    assert runner.settle_relations() == [
        ["goanno_wf", "goobo_extract", "goobo_parent_child"],
        ["go_classification_new", "go_classification_relationship_new",
         "fullgo_version_new", "go_classification_descendants"],
    ]


def test_a_settle_failure_resumes_at_the_step_after_it(capsys):
    """The make step already succeeded; re-running it would hit an ALTER TABLE
    go_annotation_old RENAME with no _old table left to rename."""
    run(FakeRunner(fail_on="go_annotation_new"))

    assert "START_AT=update_paint_go_evidence" in capsys.readouterr().out


def test_run_returns_nonzero_when_a_step_fails():
    assert run(FakeRunner(fail_on="update_paint_go_evidence")) != 0


def test_run_prints_the_resume_command_for_the_failed_step(capsys):
    run(FakeRunner(fail_on="update_paint_go_evidence"))

    assert "START_AT=update_paint_go_evidence" in capsys.readouterr().out


def test_run_prints_the_tables_affected_before_the_failure(capsys):
    """These are what scripts/util/reset_paint_table.sh has to be handed."""
    run(FakeRunner(fail_on="update_paint_go_evidence"))
    line = next(l for l in capsys.readouterr().out.splitlines() if "AFFECTED_TABLES" in l)

    assert line.split("=", 1)[1].split() == ["go_classification",
                                             "go_classification_relationship",
                                             "fullgo_version", "go_annotation"]


### The point-of-no-return gate

def test_the_switch_does_not_run_when_nothing_can_confirm_it():
    runner = FakeRunner()

    run(runner, confirmer=None)

    assert "switch_table_names_go_only" not in runner.make_targets()


def test_stopping_at_the_gate_is_not_a_failure():
    assert run(FakeRunner(), confirmer=None) == 0


def test_stopping_at_the_gate_prints_how_to_resume(capsys):
    run(FakeRunner(), confirmer=None)

    assert "START_AT=switch_table_names_go_only" in capsys.readouterr().out


def test_table_counts_are_shown_before_asking_to_confirm():
    runner = FakeRunner()
    asked_after = []

    run(runner, confirmer=lambda step: (asked_after.append(runner.make_targets()[-1]),
                                        True)[1])

    assert asked_after == ["paint_go_table_counts"]


def test_confirming_runs_the_switch_and_the_steps_after_it():
    runner = FakeRunner()

    run(runner, confirmer=lambda step: True)

    assert runner.make_targets()[-3:] == ["switch_table_names_go_only",
                                          "regenerate_go_aggregate_view",
                                          "regenerate_paint_aggregate_view"]


def test_declining_the_switch_stops_the_run():
    runner = FakeRunner()

    run(runner, confirmer=lambda step: False)

    assert "switch_table_names_go_only" not in runner.make_targets()


def test_confirm_switch_skips_the_prompt_entirely():
    runner = FakeRunner()

    def refuse_to_be_asked(step):
        raise AssertionError("should not prompt when confirm_switch is set")

    run(runner, confirm_switch=True, confirmer=refuse_to_be_asked)

    assert "switch_table_names_go_only" in runner.make_targets()


### Preflight

def test_preflight_reports_a_missing_required_file(tmp_path):
    (tmp_path / "config").mkdir()

    missing = rptu.missing_prerequisites(str(tmp_path / "2026-08-18_fullgo"),
                                         repo_root=str(tmp_path))

    assert any("profile.txt" in m for m in missing)


def test_preflight_is_satisfied_when_every_prerequisite_exists(tmp_path):
    base = tmp_path / "2026-08-18_fullgo"
    (base / "resources").mkdir(parents=True)
    (base / "profile.txt").write_text("GO\t2026-08-01\n")
    (base / "resources" / "complex_terms.tsv").write_text("GO:0032991\n")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "config.yaml").write_text("DB_DEFINITION:\n")

    assert rptu.missing_prerequisites(str(base), repo_root=str(tmp_path)) == []


def test_run_does_not_start_when_a_prerequisite_is_missing(tmp_path):
    runner = FakeRunner()

    rptu.run(rptu.STEPS, runner, base_path=str(tmp_path / "nope"),
             repo_root=str(tmp_path))

    assert runner.commands == []


def test_run_returns_nonzero_when_a_prerequisite_is_missing(tmp_path):
    rc = rptu.run(rptu.STEPS, FakeRunner(), base_path=str(tmp_path / "nope"),
                  repo_root=str(tmp_path))

    assert rc != 0


### Dry run

def test_dry_run_executes_nothing():
    runner = FakeRunner()

    run(runner, dry_run=True)

    assert runner.commands == []


def test_dry_run_lists_every_step_and_its_settle(capsys):
    run(FakeRunner(), dry_run=True)
    out = capsys.readouterr().out

    assert all(target in out for target in README_STEPS)
    assert "go_annotation_new" in out


### MakeRunner (the real subprocess runner FakeRunner stands in for elsewhere)

def test_make_runner_returns_the_commands_exit_code(tmp_path):
    runner = rptu.MakeRunner(cwd=str(tmp_path), out=io.StringIO())

    assert runner(["python3", "-c", "import sys; sys.exit(3)"]) == 3


def test_make_runner_streams_output_to_its_stream(tmp_path):
    stream = io.StringIO()
    runner = rptu.MakeRunner(cwd=str(tmp_path), out=stream)

    # The banner echoes the command, so the probe has to be something the command text
    # does not already contain - otherwise the echo alone satisfies the assertion.
    runner(["python3", "-c", "print('mapped', 20 * 20, 'rows')"])

    assert "mapped 400 rows" in stream.getvalue()


def test_make_runner_appends_output_to_the_log(tmp_path):
    log = tmp_path / "log.txt"
    log.write_text("earlier step\n")
    runner = rptu.MakeRunner(log_path=str(log), cwd=str(tmp_path), out=io.StringIO())

    runner(["python3", "-c", "print('mapped', 20 * 20, 'rows')"])

    assert log.read_text().endswith("mapped 400 rows\n")


def test_make_runner_logs_which_command_produced_the_output(tmp_path):
    """A log of bare output with no step boundaries is unreadable weeks later."""
    log = tmp_path / "log.txt"
    runner = rptu.MakeRunner(log_path=str(log), cwd=str(tmp_path), out=io.StringIO())

    runner(["python3", "-c", "print('ok')"])

    assert "$ python3 -c print('ok')" in log.read_text()


def test_make_runner_captures_stderr_too(tmp_path):
    """make writes its errors to stderr; losing them would gut the log."""
    stream = io.StringIO()
    runner = rptu.MakeRunner(cwd=str(tmp_path), out=stream)

    runner(["python3", "-c", "import sys; print('exit', 3 + 4, file=sys.stderr)"])

    assert "exit 7" in stream.getvalue()


def test_settle_timeout_is_forwarded_to_the_settle_command():
    """An anti-wraparound vacuum can outlast the settle script's default hour."""
    runner = FakeRunner()

    run(runner, rptu.select_steps(rptu.STEPS, stop_after="update_paint_go_annotation"),
        settle_timeout=7200)

    assert runner.settles()[-1] == ["python3", "scripts/settle_db_tables.py",
                                    "--schema", "panther_upl", "--timeout", "7200",
                                    "go_annotation_new"]


def test_no_settle_timeout_leaves_the_script_default_in_place():
    runner = FakeRunner()

    run(runner, rptu.select_steps(rptu.STEPS, stop_after="update_paint_go_annotation"))

    assert "--timeout" not in runner.settles()[-1]
