import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def run_create_profile(tmp_path, date_contents, doi_contents=None, date_filename="release-date.json"):
    date_file = tmp_path / date_filename
    date_file.write_text(date_contents)
    argv = [sys.executable, "scripts/create_profile.py", "-j", str(date_file)]
    if doi_contents is not None:
        doi_file = tmp_path / "release-archive-doi.json"
        doi_file.write_text(doi_contents)
        argv += ["-d", str(doi_file)]
    argv += ["-p", "19.0"]
    result = subprocess.run(argv, cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return result.stdout


def test_profile_includes_doi_row(tmp_path):
    stdout = run_create_profile(
        tmp_path, "{date: 2026-06-19}\n", '{\n  "doi": "10.5281/zenodo.20943148"\n}\n'
    )
    assert stdout.splitlines() == [
        "GO\t2026-06-19",
        "DOI GO\t10.5281/zenodo.20943148",
        "PANTHER\tv.19.0",
    ]


def test_doi_row_follows_go_row(tmp_path):
    """The *_version.sql recipes read the date with `grep GO ... | head -n 1`, which
    would pick up `DOI GO` instead if the rows were ever reordered."""
    stdout = run_create_profile(
        tmp_path, "{date: 2026-06-19}\n", '{"doi": "10.5281/zenodo.20943148"}'
    )
    go_rows = [l for l in stdout.splitlines() if "GO" in l]
    assert go_rows[0].split("\t") == ["GO", "2026-06-19"]
    assert [l for l in stdout.splitlines() if l.startswith("DOI")][0].split("\t")[1] \
        == "10.5281/zenodo.20943148"


def test_profile_omits_doi_row_when_not_passed(tmp_path):
    """GOEx publishes no DOI, so make_profile drops the flag via GO_DOI_FILE=."""
    stdout = run_create_profile(tmp_path, "2026-07-06\n", date_filename="release_date.txt")
    assert stdout.splitlines() == ["GO\t2026-07-06", "PANTHER\tv.19.0"]
