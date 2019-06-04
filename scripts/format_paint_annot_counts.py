import csv
import argparse
from pthr_db_caller.db_caller import DBCaller

parser = argparse.ArgumentParser()
parser.add_argument('-n', '--omit_no_changes', action="store_const", const=True, help="Omits writing row for families having no changed counts between versions")
args = parser.parse_args()

## Queries
query_13_1 = """
select c.accession, cc.confidence_code, count(distinct(pe.annotation_id)) from panther_upl.paint_annotation_v13_1 pa
join panther_upl.node n on n.node_id = pa.node_id
join panther_upl.classification c on c.accession = split_part(n.accession, ':', 1)
join panther_upl.paint_evidence_v13_1 pe on pe.annotation_id = pa.annotation_id
join panther_upl.confidence_code cc on cc.confidence_code_sid = pe.confidence_code_sid
where c.classification_version_sid = 24
and n.classification_version_sid = 24
group by c.accession, cc.confidence_code
order by c.accession, cc.confidence_code;
"""

query_14_1 = """
select c.accession, cc.confidence_code, count(distinct(pe.annotation_id)) from panther_upl.paint_annotation pa
join panther_upl.node n on n.node_id = pa.node_id
join panther_upl.classification c on c.accession = split_part(n.accession, ':', 1)
join panther_upl.paint_evidence pe on pe.annotation_id = pa.annotation_id
join panther_upl.confidence_code cc on cc.confidence_code_sid = pe.confidence_code_sid
where c.classification_version_sid = 26
and n.classification_version_sid = 26
group by c.accession, cc.confidence_code
order by c.accession, cc.confidence_code;
"""

caller = DBCaller()
results_14_1 = caller.run_cmd_line_args(query_14_1, no_header_footer=True)
results_13_1 = caller.run_cmd_line_args(query_13_1, no_header_footer=True)

ev_codes = []

def parse_results(results):
    counts = {}
    for r in results:
        if r[0].startswith("PTHR"):
            # PTHR row
            pthr_id = r[0]
            if pthr_id not in counts:
                counts[pthr_id] = {}
            ev_code = r[1]
            if ev_code not in ev_codes:
                ev_codes.append(ev_code)
            count = r[2]
            # if ev_code not in counts[pthr_id]:
            counts[pthr_id][ev_code] = count
    return counts

counts_14_1 = parse_results(results_14_1)
counts_13_1 = parse_results(results_13_1)
all_fams = set(list(counts_14_1.keys()) + list(counts_13_1.keys()))
print(len(all_fams))

if args.omit_no_changes:
    out_fname = "pthr_14_1_paint_annot_counts_diff_changes_only.csv"
else:
    out_fname = "pthr_14_1_paint_annot_counts_diff.csv"

out_f = open(out_fname, "w+")
writer = csv.writer(out_f)
top_row = ["Family"]
for ev in ev_codes:
    top_row.append("{}s in 14.1".format(ev))
    top_row.append("# {} change".format(ev))
writer.writerow(top_row)
for pthr in all_fams:
    row = [pthr]
    row_diffs = []
    for ev in ev_codes:
        # 13.1
        if pthr in counts_13_1 and ev in counts_13_1[pthr]:
            count_13_1 = counts_13_1[pthr][ev]
        else:
            count_13_1 = 0

        # 14.1
        if pthr in counts_14_1 and ev in counts_14_1[pthr]:
            count_14_1 = counts_14_1[pthr][ev]
        else:
            count_14_1 = 0
        diff = count_14_1 - count_13_1
        row.append(count_14_1)
        row.append(diff)
        row_diffs.append(diff)
    if args.omit_no_changes and set(row_diffs) == set([0]):
        continue
    else:
        writer.writerow(row)

out_f.close()