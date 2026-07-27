import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from util.release_date import read_release_date  # noqa: E402
from make_readme import relative_to_base  # noqa: E402

LBL_CURRENT_URL = "https://current.geneontology.org/"
GOEX_CURRENT_URL = "https://ftp.ebi.ac.uk/pub/contrib/goa/goex/current/"
GOEX_RELEASE_URL = "https://ftp.ebi.ac.uk/pub/contrib/goa/goex/releases/"


@pytest.mark.parametrize("url,base_url,expected", [
    # The GO listing hands back absolute http:// hrefs for an https:// base
    ("http://current.geneontology.org/annotations/gaf/ACIB2-uniprot.gaf.gz", LBL_CURRENT_URL,
     "annotations/gaf/ACIB2-uniprot.gaf.gz"),
    ("https://current.geneontology.org/annotations/gaf/ACIB2-uniprot.gaf.gz", LBL_CURRENT_URL,
     "annotations/gaf/ACIB2-uniprot.gaf.gz"),
    ("https://current.geneontology.org/ontology/go.obo", LBL_CURRENT_URL, "ontology/go.obo"),
    # GOEx base URL carries a path prefix that also has to come off
    (f"{GOEX_CURRENT_URL}uniprot-centric/gaf/CHICK_9031_UP000000539.gaf.gz", GOEX_CURRENT_URL,
     "uniprot-centric/gaf/CHICK_9031_UP000000539.gaf.gz"),
])
def test_relative_to_base(url, base_url, expected):
    assert relative_to_base(url, base_url) == expected


@pytest.mark.parametrize("filename,contents,expected", [
    # LBL release-date.json, well-formed (through the 2024 releases)
    ("release-date.json", '{\n    "date": "2024-06-17"\n}\n', "2024-06-17"),
    # LBL release-date.json, unquoted key and value (2026-06-19 release)
    ("release-date.json", "{date: 2026-06-19}\n", "2026-06-19"),
    # GOEx release_date.txt
    ("release_date.txt", "2026-07-06\n", "2026-07-06"),
])
def test_read_release_date(tmp_path, filename, contents, expected):
    path = tmp_path / filename
    path.write_text(contents)
    assert read_release_date(str(path)) == expected


def test_read_release_date_rejects_undated_file(tmp_path):
    path = tmp_path / "release-date.json"
    path.write_text('{"doi": "10.5281/zenodo.20943148"}')
    with pytest.raises(ValueError, match="No release date found"):
        read_release_date(str(path))


def run_make_readme(tmp_path, date_file, downloaded_urls, extra_args=()):
    (tmp_path / date_file[0]).write_text(date_file[1])
    downloaded = tmp_path / "downloaded_files.txt"
    downloaded.write_text("".join(f"{u}\n" for u in downloaded_urls))
    result = subprocess.run(
        [sys.executable, "scripts/make_readme.py",
         "-r", str(tmp_path / date_file[0]), "-d", str(downloaded), *extra_args],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    return result.stdout


def test_make_readme_defaults_to_lbl_urls(tmp_path):
    stdout = run_make_readme(
        tmp_path,
        ("release-date.json", "{date: 2026-06-19}\n"),
        ["https://current.geneontology.org/ontology/go.obo",
         "https://current.geneontology.org/annotations/goa_human-uniprot.gaf.gz"],
    )
    assert "GO release date: 2026-06-19" in stdout
    assert "https://release.geneontology.org/2026-06-19/ontology/go.obo" in stdout
    assert "https://release.geneontology.org/2026-06-19/annotations/goa_human-uniprot.gaf.gz" in stdout
    assert "retrieved at any time from https://release.geneontology.org/2026-06-19" in stdout


def test_make_readme_accepts_goex_urls(tmp_path):
    stdout = run_make_readme(
        tmp_path,
        ("release_date.txt", "2026-07-06\n"),
        [f"{GOEX_CURRENT_URL}uniprot-centric/gaf/CHICK_9031_UP000000539.gaf.gz"],
        extra_args=("-c", GOEX_CURRENT_URL, "-b", GOEX_RELEASE_URL),
    )
    assert "GO release date: 2026-07-06" in stdout
    assert f"{GOEX_RELEASE_URL}2026-07-06/uniprot-centric/gaf/CHICK_9031_UP000000539.gaf.gz" in stdout


def test_make_readme_rewrites_http_hrefs_against_https_base(tmp_path):
    """download_files logs the listing's absolute http:// hrefs verbatim."""
    stdout = run_make_readme(
        tmp_path,
        ("release-date.json", "{date: 2026-06-19}\n"),
        ["http://current.geneontology.org/annotations/gaf/ACIB2-uniprot.gaf.gz"],
    )
    assert "https://release.geneontology.org/2026-06-19/annotations/gaf/ACIB2-uniprot.gaf.gz" in stdout
    assert "http://current.geneontology.org" not in stdout


def test_make_readme_handles_empty_download_list(tmp_path):
    """dated_release_base_url used to be computed inside the loop."""
    stdout = run_make_readme(tmp_path, ("release-date.json", "{date: 2026-06-19}\n"), [])
    assert "retrieved at any time from https://release.geneontology.org/2026-06-19" in stdout
