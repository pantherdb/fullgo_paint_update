from pthr_db_caller.db_caller import DBCaller
from util.publish_google_sheet import SheetPublishHandler, Sheet
from os import path
import csv
import argparse
import yaml
import datetime

parser = argparse.ArgumentParser()
# parser.add_argument('outfile')
parser.add_argument('-r', '--reload_data', action="store_const", const=True)
args = parser.parse_args()

CALLER = DBCaller()
A_DATA = None
B_DATA = None
ALL_FAMS = []  # Just to be safe

query = """
select split_part(n.accession,':',1), count(*) from panther_upl.{} pa
join panther_upl.node n on n.node_id = pa.node_id
where pa.obsolescence_date is null
group by split_part(n.accession,':',1);
"""


def get_results(table_name, cache_file, reload_data=None):
    
    # Cache results
    if path.isfile(cache_file) and not reload_data:
        results = []
        with open(cache_file) as cf:
            reader = csv.reader(cf, delimiter=";")
            results = [r for r in reader]
    else:
        results = CALLER.run_cmd_line_args(query.format(table_name), rows_outfile=cachefile, no_header_footer=True)
    return results


def parse_fam_results(results_list):
    results_list = results_list[1:]
    version_counts = {}  # PTHR-to-counts
    for r in results_list:
        family = r[0]
        annot_count = r[1]
        version_counts[family] = annot_count
        if family not in ALL_FAMS:
            ALL_FAMS.append(family)
    return version_counts


if __name__ == "__main__":
    # Parameterize
    # table_13_1 = "paint_annotation_v13_1"
    # table_14_1 = "paint_annotation"
    A_DATA = yaml.safe_load(open(args.a_yaml))
    B_DATA = yaml.safe_load(open(args.b_yaml))
    table_a = A_DATA["table_name"]
    table_b = B_DATA["table_name"]

    cachefile = "scripts/sql/cache/version_family_node_counts.{}.txt"
    results_a = get_results(table_a, cachefile.format(table_a), reload_data=args.reload_data)
    results_b = get_results(table_b, cachefile.format(table_b), reload_data=args.reload_data)

    ver_a = parse_fam_results(results_a)
    ver_b = parse_fam_results(results_b)

    # Write this sucka out
    handler = SheetPublishHandler()
    sheet_title = "{}-version_paint_annot_counts".format(datetime.date.today().isoformat())
    sheet = Sheet(title=sheet_title)
    outfile = "{}.tsv".format(sheet_title)
    out_f = open(outfile, "w+")
    writer = csv.writer(out_f, delimiter="\t")
    headers = ["Family", A_DATA["data_title"], B_DATA["data_title"]]
    writer.writerow(headers)
    sheet.append_row(headers)
    ALL_FAMS.sort()
    for f in ALL_FAMS:
        row = [f, ver_a.get(f), ver_b.get(f)]
        writer.writerow(row)
        sheet.append_row(row)
        # break

    out_f.close()
    handler.publish_sheet(sheet)