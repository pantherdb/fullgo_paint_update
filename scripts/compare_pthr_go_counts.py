"""QA report: by-proteome annotation counts in Pthr_GO_<version>.tsv, previous vs current.

Catches a GAF source or ID-mapping change that quietly guts a proteome. Swapping ECOLI
from a UniProt-centric GAF to a MOD-centric (DB prefix=EcoCyc) one, for instance, broke
mapping in fullGoMappingPthrHierarchy.pl and dropped 54,316 annotations to 677.

Run it after slurm_fullGoMappingPthr and before load_raw_go_to_panther:

    python3 scripts/compare_pthr_go_counts.py -b 2026-07-27_fullgo/Pthr_GO_19.0.tsv \\
        -a 2026-08-10_fullgo/Pthr_GO_19.0.tsv -o 2026-08-10_fullgo/pthr_go_count_diff.tsv

Exits 1 when any proteome deviates by at least --threshold percent so the recipe fails
loudly; --no_fail makes it advisory.
"""

import argparse
import contextlib
import csv
import gzip
import io
import os
import sys
import tarfile
from collections import Counter, defaultdict, namedtuple

parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
parser.add_argument('-b', '--before_pthr_go', required=True,
                    help="Previous release's Pthr_GO_<version>.tsv (.gz and .tar.gz also accepted; "
                         "a plain .tsv name resolves to either archive)")
parser.add_argument('-a', '--after_pthr_go', required=True,
                    help="Current release's Pthr_GO_<version>.tsv")
parser.add_argument('-t', '--threshold', type=float, default=10.0,
                    help="Flag a proteome deviating by at least this percent (default 10.0)")
parser.add_argument('-m', '--min_annotations', type=int, default=0,
                    help="Skip flagging proteomes with fewer annotations than this in both "
                         "releases; tiny proteomes swing wildly (default 0, flag everything)")
parser.add_argument('-o', '--outfile', help="Also write the report as TSV to this path")
parser.add_argument('--no_fail', action='store_true',
                    help="Always exit 0, even when proteomes are flagged")

# Annotation rows and the distinct gene products they came from. Rows answer "how many
# annotations"; gene products are the more direct read on ID-mapping health.
ProteomeCounts = namedtuple("ProteomeCounts", ["annotations", "gene_products"])

ProteomeDiff = namedtuple("ProteomeDiff", [
    "proteome",
    "annotations_before", "annotations_after", "annotations_delta", "annotations_pct",
    "gene_products_before", "gene_products_after", "gene_products_delta", "gene_products_pct",
])

REPORT_COLUMNS = ["proteome", "annot_before", "annot_after", "annot_delta", "annot_pct",
                  "gp_before", "gp_after", "gp_delta", "gp_pct", "flag"]

ARCHIVE_SUFFIXES = ("", ".gz", ".tar.gz")


def resolve_pthr_go_path(path):
    """Find the Pthr_GO file, allowing for the archiving a finished release gets.

    Completed releases keep Pthr_GO as .tsv.tar.gz (or .tsv.gz), so a caller naming the
    plain .tsv still finds last month's file.
    """
    for suffix in ARCHIVE_SUFFIXES:
        candidate = f"{path}{suffix}"
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError(f"No Pthr_GO file at {path} (also tried .gz and .tar.gz)")


def _first_tar_member(tar, path):
    for member in tar:
        if member.isfile():
            return tar.extractfile(member)
    raise RuntimeError(f"No file member found in {path}")


@contextlib.contextmanager
def open_pthr_go(path):
    """Yield line iteration over a plain, gzipped, or tarred-gzipped Pthr_GO TSV.

    Streams throughout - the uncompressed file runs to ~2GB.
    """
    resolved = resolve_pthr_go_path(path)
    if resolved.endswith((".tar.gz", ".tgz")):
        with tarfile.open(resolved, mode="r:gz") as tar:
            with io.TextIOWrapper(_first_tar_member(tar, resolved), encoding="utf-8") as text:
                yield text
    elif resolved.endswith(".gz"):
        with gzip.open(resolved, mode="rt", encoding="utf-8") as text:
            yield text
    else:
        with open(resolved, encoding="utf-8") as text:
            yield text


def count_by_proteome(lines):
    """Tally annotation rows and distinct gene products per proteome code.

    Field 1 of a Pthr_GO row is the gene product, "OSCODE|db=id|UniProtKB=accession", so
    the proteome is everything before the first pipe.
    """
    annotations = Counter()
    gene_products = defaultdict(set)
    for line in lines:
        gene_product = line.split("\t", 1)[0].strip()
        if not gene_product:
            continue
        proteome = gene_product.split("|", 1)[0]
        annotations[proteome] += 1
        gene_products[proteome].add(gene_product)
    return {p: ProteomeCounts(annotations[p], len(gene_products[p])) for p in annotations}


def _percent_change(before, after):
    """None means the proteome is absent from the before release - no percent is defined."""
    if before == 0:
        return None
    return (after - before) / before * 100


def _sort_magnitude(diff):
    """How far this proteome moved, taking whichever metric moved further.

    A collapsed ID mapping that leaves the row count alone still sorts to the top.
    """
    percents = (diff.annotations_pct, diff.gene_products_pct)
    if any(p is None for p in percents):
        return float("inf")
    return max(abs(p) for p in percents)


def compare_counts(before, after):
    """Diff two count_by_proteome() results, greatest percent deviation first."""
    empty = ProteomeCounts(0, 0)
    diffs = []
    for proteome in set(before) | set(after):
        b = before.get(proteome, empty)
        a = after.get(proteome, empty)
        diffs.append(ProteomeDiff(
            proteome,
            b.annotations, a.annotations, a.annotations - b.annotations,
            _percent_change(b.annotations, a.annotations),
            b.gene_products, a.gene_products, a.gene_products - b.gene_products,
            _percent_change(b.gene_products, a.gene_products),
        ))
    diffs.sort(key=lambda d: (-_sort_magnitude(d), d.proteome))
    return diffs


def is_flagged(diff, threshold, min_annotations=0):
    """Does this proteome deviate enough to be worth a look before the DB load?"""
    if max(diff.annotations_before, diff.annotations_after) < min_annotations:
        return False
    if diff.annotations_before == 0 or diff.annotations_after == 0:
        return True  # appeared or vanished outright, whatever the threshold
    return (abs(diff.annotations_pct) >= threshold
            or abs(diff.gene_products_pct) >= threshold)


def _format_percent(pct):
    return "new" if pct is None else f"{pct:+.1f}"


def report_row(diff, flagged):
    """One report line as strings, shared by the stdout table and the TSV."""
    return [
        diff.proteome,
        str(diff.annotations_before), str(diff.annotations_after), str(diff.annotations_delta),
        _format_percent(diff.annotations_pct),
        str(diff.gene_products_before), str(diff.gene_products_after),
        str(diff.gene_products_delta), _format_percent(diff.gene_products_pct),
        "FLAG" if flagged else "",
    ]


def _totals_row(diffs):
    annot_before = sum(d.annotations_before for d in diffs)
    annot_after = sum(d.annotations_after for d in diffs)
    gp_before = sum(d.gene_products_before for d in diffs)
    gp_after = sum(d.gene_products_after for d in diffs)
    return ["TOTAL",
            str(annot_before), str(annot_after), str(annot_after - annot_before),
            _format_percent(_percent_change(annot_before, annot_after)),
            str(gp_before), str(gp_after), str(gp_after - gp_before),
            _format_percent(_percent_change(gp_before, gp_after)),
            ""]


def format_report(diffs, flags, threshold, min_annotations=0):
    """Aligned table plus totals and a one-line verdict."""
    rows = [REPORT_COLUMNS] + [report_row(d, flags[d.proteome]) for d in diffs]
    rows.append(_totals_row(diffs))
    widths = [max(len(row[i]) for row in rows) for i in range(len(REPORT_COLUMNS))]

    def render(row):
        return "  ".join(
            cell.ljust(widths[i]) if i == 0 else cell.rjust(widths[i])
            for i, cell in enumerate(row)
        ).rstrip()

    lines = [render(rows[0])]
    lines.extend(render(row) for row in rows[1:-1])
    lines.append("-" * len(lines[0]))
    lines.append(render(rows[-1]))
    lines.append("")
    flagged = sum(1 for f in flags.values() if f)
    summary = f"{flagged} of {len(diffs)} proteomes exceed {threshold}% deviation"
    if min_annotations:
        summary += f" (ignoring proteomes under {min_annotations} annotations)"
    lines.append(summary)
    return "\n".join(lines)


def write_tsv(outfile, diffs, flags):
    with open(outfile, "w", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(REPORT_COLUMNS)
        for diff in diffs:
            writer.writerow(report_row(diff, flags[diff.proteome]))
        writer.writerow(_totals_row(diffs))


def main(argv=None):
    args = parser.parse_args(argv)

    with open_pthr_go(args.before_pthr_go) as lines:
        before = count_by_proteome(lines)
    with open_pthr_go(args.after_pthr_go) as lines:
        after = count_by_proteome(lines)

    diffs = compare_counts(before, after)
    flags = {d.proteome: is_flagged(d, args.threshold, args.min_annotations) for d in diffs}

    print(format_report(diffs, flags, args.threshold, args.min_annotations))
    if args.outfile:
        write_tsv(args.outfile, diffs, flags)

    if any(flags.values()) and not args.no_fail:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
