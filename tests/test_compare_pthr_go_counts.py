"""Tests for the by-proteome annotation count QA report.

The failure this guards against: swapping a species' GAF source (e.g. ECOLI from a
UniProt-centric GAF to a MOD-centric EcoCyc one) breaks ID mapping in
fullGoMappingPthrHierarchy.pl and silently drops tens of thousands of annotations from
Pthr_GO_<version>.tsv.
"""

import gzip
import os
import sys
import tarfile

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import compare_pthr_go_counts as cpgc  # noqa: E402


def pthr_go_line(proteome, accession, go_term):
    """One Pthr_GO row: gene product, term, qualifier, evidence, with_from, reference, assigned_by."""
    gene_product = f"{proteome}|Ensembl=ENS{accession}|UniProtKB={accession}"
    return "\t".join([gene_product, go_term, "", "IEA", "", "GO_REF:0000002", "InterPro"])


def write_pthr_go(path, rows):
    """rows: (proteome, accession, go_term) triples."""
    with open(path, "w") as f:
        for row in rows:
            f.write(pthr_go_line(*row) + "\n")
    return str(path)


def counts(**by_proteome):
    """counts(ECOLI=(54316, 3973)) -> {"ECOLI": ProteomeCounts(54316, 4438)}"""
    return {p: cpgc.ProteomeCounts(*v) for p, v in by_proteome.items()}


def diff_for(proteome, before, after):
    """Build the single ProteomeDiff for one proteome; pass None for absent from a release."""
    before_counts = {} if before is None else counts(**{proteome: before})
    after_counts = {} if after is None else counts(**{proteome: after})
    return cpgc.compare_counts(before_counts, after_counts)[0]


### count_by_proteome

def test_count_by_proteome_counts_rows_and_distinct_gene_products():
    lines = [
        pthr_go_line("ECOLI", "P0A7B8", "GO:0000166"),
        pthr_go_line("ECOLI", "P0A7B8", "GO:0004087"),  # same gene product, second annotation
        pthr_go_line("ECOLI", "P0A7C1", "GO:0005524"),
        pthr_go_line("HUMAN", "Q9Y6K9", "GO:0005524"),
    ]
    assert cpgc.count_by_proteome(lines) == counts(ECOLI=(3, 2), HUMAN=(1, 1))


def test_count_by_proteome_skips_blank_lines():
    lines = [pthr_go_line("ECOLI", "P0A7B8", "GO:0000166"), "\n", "", "\n"]
    assert cpgc.count_by_proteome(lines) == counts(ECOLI=(1, 1))


### open_pthr_go

PLAIN_ROWS = [("ECOLI", "P0A7B8", "GO:0000166"), ("HUMAN", "Q9Y6K9", "GO:0005524")]


def test_open_pthr_go_reads_plain_tsv(tmp_path):
    path = write_pthr_go(tmp_path / "Pthr_GO_19.0.tsv", PLAIN_ROWS)
    with cpgc.open_pthr_go(path) as lines:
        assert cpgc.count_by_proteome(lines) == counts(ECOLI=(1, 1), HUMAN=(1, 1))


def test_open_pthr_go_reads_gzipped_tsv(tmp_path):
    """The filtered TSV ships as a plain .gz."""
    path = tmp_path / "Pthr_GO_19.0.tsv.gz"
    with gzip.open(path, "wt") as f:
        f.write(pthr_go_line("ECOLI", "P0A7B8", "GO:0000166") + "\n")
    with cpgc.open_pthr_go(str(path)) as lines:
        assert cpgc.count_by_proteome(lines) == counts(ECOLI=(1, 1))


def make_tar_gz(tmp_path, member_rows):
    """Archived releases keep Pthr_GO as a real tar.gz holding the single .tsv."""
    inner = write_pthr_go(tmp_path / "inner.tsv", member_rows)
    archive = tmp_path / "Pthr_GO_19.0.tsv.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(inner, arcname="Pthr_GO_19.0.tsv")
    os.remove(inner)
    return archive


def test_open_pthr_go_reads_tarred_gzipped_tsv(tmp_path):
    archive = make_tar_gz(tmp_path, PLAIN_ROWS)
    with cpgc.open_pthr_go(str(archive)) as lines:
        assert cpgc.count_by_proteome(lines) == counts(ECOLI=(1, 1), HUMAN=(1, 1))


def test_open_pthr_go_resolves_archived_path_from_plain_name(tmp_path):
    """The Makefile names the plain .tsv; last month's release is only there as .tsv.tar.gz."""
    make_tar_gz(tmp_path, PLAIN_ROWS)
    with cpgc.open_pthr_go(str(tmp_path / "Pthr_GO_19.0.tsv")) as lines:
        assert cpgc.count_by_proteome(lines) == counts(ECOLI=(1, 1), HUMAN=(1, 1))


def test_open_pthr_go_raises_when_no_candidate_exists(tmp_path):
    with pytest.raises(FileNotFoundError):
        with cpgc.open_pthr_go(str(tmp_path / "Pthr_GO_19.0.tsv")):
            pass


### compare_counts

def test_compare_counts_computes_percent_change_per_metric():
    """Measured numbers from the ECOLI regression: 2026-07-27 -> 2026-08-10."""
    diff = diff_for("ECOLI", before=(54316, 3973), after=(677, 23))
    assert diff.annotations_delta == -53639
    assert diff.annotations_pct == pytest.approx(-98.75, abs=0.01)
    assert diff.gene_products_delta == -3950
    assert diff.gene_products_pct == pytest.approx(-99.42, abs=0.01)


def test_compare_counts_reports_disappeared_proteome_as_minus_100():
    diff = diff_for("SCHJY", before=(42549, 4145), after=None)
    assert (diff.annotations_after, diff.gene_products_after) == (0, 0)
    assert diff.annotations_pct == pytest.approx(-100.0)


def test_compare_counts_reports_new_proteome_without_a_percent():
    """No 'before' means no percent is defined; the report renders this as 'new'."""
    diff = diff_for("PSEAE", before=None, after=(31643, 3011))
    assert diff.annotations_before == 0
    assert diff.annotations_pct is None
    assert diff.gene_products_pct is None


def test_compare_counts_sorts_by_greatest_percent_diff():
    before = counts(ECOLI=(54316, 3973), DANRE=(141825, 25311), RAT=(531894, 21588))
    after = counts(ECOLI=(677, 23), DANRE=(205275, 27904), RAT=(543084, 21600))
    assert [d.proteome for d in cpgc.compare_counts(before, after)] == ["ECOLI", "DANRE", "RAT"]


def test_compare_counts_sorts_new_and_disappeared_proteomes_first():
    before = counts(SCHJY=(42549, 4145), ECOLI=(54316, 3973))
    after = counts(ECOLI=(677, 23), PSEAE=(31643, 3011))
    assert [d.proteome for d in cpgc.compare_counts(before, after)][:2] == ["PSEAE", "SCHJY"]


def test_compare_counts_sorts_on_gene_products_when_rows_hold_flat():
    """A collapsed ID mapping that leaves the row count alone must not hide below noise."""
    before = counts(BROKEN=(1000, 500), NOISY=(1000, 500))
    after = counts(BROKEN=(1000, 50), NOISY=(1050, 525))
    assert [d.proteome for d in cpgc.compare_counts(before, after)] == ["BROKEN", "NOISY"]


### is_flagged

def test_is_flagged_at_threshold():
    diff = diff_for("XENLA", before=(342375, 30000), after=(203089, 27000))
    assert cpgc.is_flagged(diff, threshold=10.0)


def test_is_flagged_false_below_threshold():
    diff = diff_for("RAT", before=(531894, 21588), after=(543084, 21600))
    assert not cpgc.is_flagged(diff, threshold=10.0)


def test_is_flagged_on_gene_products_alone():
    diff = diff_for("BROKEN", before=(1000, 500), after=(1000, 50))
    assert cpgc.is_flagged(diff, threshold=10.0)


def test_is_flagged_always_flags_a_disappeared_proteome():
    """A proteome vanishing is always worth a look, whatever the threshold."""
    diff = diff_for("SCHJY", before=(42549, 4145), after=None)
    assert cpgc.is_flagged(diff, threshold=500.0)


def test_is_flagged_always_flags_a_new_proteome():
    diff = diff_for("PSEAE", before=None, after=(31643, 3011))
    assert cpgc.is_flagged(diff, threshold=500.0)


def test_is_flagged_skips_proteomes_below_min_annotations():
    """Tiny proteomes swing wildly; --min_annotations keeps them out of the flag list."""
    diff = diff_for("IXOSC", before=(462, 100), after=(499, 108))
    assert cpgc.is_flagged(diff, threshold=5.0)
    assert not cpgc.is_flagged(diff, threshold=5.0, min_annotations=1000)


### main

def before_after_files(tmp_path, before_rows, after_rows):
    return (write_pthr_go(tmp_path / "before.tsv", before_rows),
            write_pthr_go(tmp_path / "after.tsv", after_rows))


def test_main_exits_nonzero_when_a_proteome_is_flagged(tmp_path, capsys):
    before, after = before_after_files(
        tmp_path,
        [("ECOLI", f"P{i}", "GO:0000166") for i in range(100)],
        [("ECOLI", "P0", "GO:0000166")],
    )
    assert cpgc.main(["-b", before, "-a", after]) == 1
    assert "ECOLI" in capsys.readouterr().out


def test_main_exits_zero_with_no_fail(tmp_path, capsys):
    before, after = before_after_files(
        tmp_path,
        [("ECOLI", f"P{i}", "GO:0000166") for i in range(100)],
        [("ECOLI", "P0", "GO:0000166")],
    )
    assert cpgc.main(["-b", before, "-a", after, "--no_fail"]) == 0


def test_main_exits_zero_when_every_proteome_is_within_threshold(tmp_path, capsys):
    rows = [("ECOLI", f"P{i}", "GO:0000166") for i in range(100)]
    before, after = before_after_files(tmp_path, rows, rows)
    assert cpgc.main(["-b", before, "-a", after]) == 0
    out = capsys.readouterr().out
    assert "0 of 1 proteomes" in out


def test_main_report_includes_totals(tmp_path, capsys):
    before, after = before_after_files(
        tmp_path,
        [("ECOLI", "P0", "GO:0000166"), ("HUMAN", "Q0", "GO:0005524")],
        [("HUMAN", "Q0", "GO:0005524")],
    )
    cpgc.main(["-b", before, "-a", after, "--no_fail"])
    out = capsys.readouterr().out
    assert "TOTAL" in out
    assert "2" in out and "1" in out


def test_main_writes_tsv_outfile(tmp_path, capsys):
    before, after = before_after_files(
        tmp_path,
        [("ECOLI", "P0", "GO:0000166"), ("ECOLI", "P1", "GO:0004087")],
        [("ECOLI", "P0", "GO:0000166")],
    )
    outfile = tmp_path / "pthr_go_count_diff.tsv"
    cpgc.main(["-b", before, "-a", after, "-o", str(outfile), "--no_fail"])
    lines = outfile.read_text().splitlines()
    assert lines[0].split("\t") == cpgc.REPORT_COLUMNS
    ecoli = dict(zip(cpgc.REPORT_COLUMNS, lines[1].split("\t")))
    assert ecoli["proteome"] == "ECOLI"
    assert (ecoli["annot_before"], ecoli["annot_after"], ecoli["annot_delta"]) == ("2", "1", "-1")
    assert ecoli["flag"] == "FLAG"
