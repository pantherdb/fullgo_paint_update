# Could only be relevant to migration?
import os
import csv
import datetime
import argparse
from util.publish_google_sheet import SheetPublishHandler, Sheet
from util.pthr_data import MOD_ORGS

parser = argparse.ArgumentParser()
parser.add_argument('-m', '--mods_only', action='store_const', const=True)

LEAVES = {}
with open("resources/nodeMapping_leaf_0_14_1.out") as lf:
    for leaf in lf.readlines():
        leaf_bits = leaf.split("\t")
        accession = leaf_bits[0]
        ptn = leaf_bits[1]
        LEAVES[ptn] = accession  # Checking lines with PTN

def get_iba_counts_from_dir(dir_path, dataset_title, results_dict=None, mods_only=None):
    if results_dict is None:
        results_dict = {}
    for gaf in os.listdir(dir_path):
        gaf_f = open("{}/{}".format(dir_path, gaf))
        for l in gaf_f.readlines():
            if not l.startswith("!"):
                parts = l.split("\t")
                syn_col = parts[10]  # Will contain our leaf PTN
                syn_bits = syn_col.split("|")
                syn_ptn = None
                for sb in syn_bits:
                    if sb.startswith("PTN"):
                        syn_ptn = sb
                        break
                if syn_ptn is None or syn_ptn not in LEAVES.keys():
                    continue  # Leaf not shared between 13.1 and 14.1 so skip
                if mods_only:
                    taxon = parts[12]
                    if taxon not in MOD_ORGS:
                        continue
                leaf_accession = LEAVES[syn_ptn]
                family = leaf_accession.split(":")[0]
                go_term = parts[4]
                with_from = parts[7]
                with_froms = with_from.split("|")
                panther_ibd = with_froms[0]  # Assuming PANTHER is first
                ibd_node = panther_ibd.split(":")[1]
                if family not in results_dict:
                    results_dict[family] = {}
                if go_term not in results_dict[family]:
                    results_dict[family][go_term] = {}
                if dataset_title not in results_dict[family][go_term]:
                    results_dict[family][go_term][dataset_title] = []
                results_dict[family][go_term][dataset_title].append(ibd_node)
    return results_dict

def get_iba_count_results(before_dir_path, after_dir_path, mods_only=None):
    family_annots = {}
    family_annots = get_iba_counts_from_dir(before_dir_path, "before", results_dict=family_annots, mods_only=mods_only)
    family_annots = get_iba_counts_from_dir(after_dir_path, "after", results_dict=family_annots, mods_only=mods_only)
    return family_annots

# Data model - need "before" and "after" keys under term to simplify writing out results
# results = {
#     "PTHR10000": {
#         "GO:0005515": {
#             "before": ["PTN000371608", "PTN000371608", "PTN001202348"],  # List occurrences (not distinct) of IBD PTNs from lines. Count these later.
#             "after": []
#         },
#         "GO:0382943": {
#             "before": [],
#             "after": ["PTN000371608", "PTN000371608", "PTN001202348"]
#         }
#     }
# }
before_iba_gaf_dir = "2019-06-17_fullgo_13_1/IBA_GAFs/"
after_iba_gaf_dir = "2019-06-25_fullgo/IBA_GAFs/"

if __name__ == "__main__":
    args = parser.parse_args()
    
    results = get_iba_count_results(before_iba_gaf_dir, after_iba_gaf_dir, mods_only=args.mods_only)
    handler = SheetPublishHandler()
    sheet_title = "{}-tracked_leaf_iba_count".format(datetime.date.today().isoformat())
    if args.mods_only:
        sheet_title += "_mods_only"
    else:
        sheet_title += "_all"
    sheet = Sheet(title=sheet_title)
    sheet.append_row([
        "Family",
        "GO term",
        "Diff",
        "14.1 ancestors",
        "13.1 ancestors"
    ])

    print("All fams:", len(results))
    rows_to_write = []
    for f in results:
        for go_term in results[f]:
            if "before" in results[f][go_term]:
                before_anc_ptns = results[f][go_term]["before"]
            else:
                before_anc_ptns = []
            if "after" in results[f][go_term]:
                after_anc_ptns = results[f][go_term]["after"]
            else:
                after_anc_ptns = []
            count_diff = len(after_anc_ptns) - len(before_anc_ptns)
            if count_diff != 0:
                row_to_write = [f, go_term, count_diff, ",".join(list(set(after_anc_ptns))), ",".join(list(set(before_anc_ptns)))]
                rows_to_write.append(row_to_write)
                sheet.append_row(row_to_write)
                # print(row_to_write)

    handler.publish_sheet(sheet)