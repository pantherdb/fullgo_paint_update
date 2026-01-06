import csv
import yaml
import os
import datetime
import argparse
from util.publish_google_sheet import SheetPublishHandler, Sheet
from util.pthr_data import MOD_ORGS

parser = argparse.ArgumentParser()
parser.add_argument('-a', '--a_yaml')
parser.add_argument('-b', '--b_yaml')
parser.add_argument('-m', '--mods_only', action='store_const', const=True)

# Diff lookups for versions?
FAM_LOOKUP = {}
# Data model
# FAM_LOOKUP = {
#     "PTN12345678": {
#         24: "PTHR14567",
#         26: "PTHR14567",
#     }
# }

A_DATA = None
B_DATA = None


def query_ds_by_ptn_and_term(ds, ptn, term):
    # ds = ibd_nodes data structure
    terms_for_ptn = ds.get(ptn)
    if terms_for_ptn:
        return terms_for_ptn.get(term)


# Data model:
# ibd_nodes = {
#     "PTN12345678": {
#         "GO:123456": 34,
#     },
#     "PTN13948232": {
#         "GO:123456": 23,
#     }
# }
def get_ibd_counts_from_dir(dir_path, mods_only=None):
    ibd_nodes = {}
    for gaf in os.listdir(dir_path):
        if gaf == "gene_association.paint_exp.gaf":
            continue
        gaf_f = open("{}/{}".format(dir_path, gaf))
        for l in gaf_f.readlines():
            if not l.startswith("!"):
                parts = l.split("\t")
                if mods_only:
                    taxon = parts[12]
                    if taxon not in MOD_ORGS:
                        continue
                go_term = parts[4]
                with_from = parts[7]
                with_froms = with_from.split("|")
                # Assuming PANTHER is first
                panther_ibd = with_froms[0]
                # print(parts)
                try:
                    ibd_node = panther_ibd.split(":")[1]
                except:
                    print(panther_ibd)
                    ibd_node = panther_ibd.split(":")[1]
                if ibd_node not in ibd_nodes:
                    ibd_nodes[ibd_node] = {}
                if go_term not in ibd_nodes[ibd_node]:
                    ibd_nodes[ibd_node][go_term] = 0
                ibd_nodes[ibd_node][go_term] += 1
    return ibd_nodes


def get_iba_gafs_by_ibd_ptn_list(ibd_ptns, dir_path, mods_only=None):
    found_lines = []
    for gaf in os.listdir(dir_path):
        with open("{}/{}".format(dir_path, gaf)) as gaf_f:
            for l in gaf_f.readlines():
                if not l.startswith("!"):
                    parts = l.split("\t")
                    if mods_only:
                        taxon = parts[12]
                        if taxon not in MOD_ORGS:
                            continue
                    with_from = parts[7]
                    with_froms = with_from.split("|")
                    # Assuming PANTHER is first
                    panther_ibd = with_froms[0]
                    try:
                        ibd_node = panther_ibd.split(":")[1]
                    except:
                        print(panther_ibd)
                        ibd_node = panther_ibd.split(":")[1]
                    if ibd_node in ibd_ptns:
                        found_lines.append(l)
    return found_lines


def get_family_for_ptn(node_ptn, cls_ver_id):
    return FAM_LOOKUP[cls_ver_id].get(node_ptn)

def parse_and_load_node(lookup, cls_ver_id, node_dat_path):
    lookup[cls_ver_id] = {}
    with open(node_dat_path) as af:
        for l in af.readlines():
            bits = l.split("\t")
            acc = bits[0]
            fam = acc.split(":")[0]
            ptn = bits[1]
            lookup[cls_ver_id][ptn] = fam
    return lookup


def load_fam_lookup(lookup):
    lookup = parse_and_load_node(lookup, A_DATA["classification_version_sid"], A_DATA["node_dat_path"])
    if A_DATA["node_dat_path"] == B_DATA["node_dat_path"]:
        lookup[B_DATA["classification_version_sid"]] = lookup[A_DATA["classification_version_sid"]]
    else:
        lookup = parse_and_load_node(lookup, B_DATA["classification_version_sid"], B_DATA["node_dat_path"])
    return lookup


if __name__ == "__main__":
    args = parser.parse_args()

    outfile = "iba_count_diff.tsv"
    outf = open(outfile, "w+")
    writer = csv.writer(outf, delimiter="\t")
    handler = SheetPublishHandler()
    sheet_title = "{}-iba_count".format(datetime.date.today().isoformat())
    if args.mods_only:
        sheet_title += "_mods_only"
    else:
        sheet_title += "_all"
    sheet = Sheet(title=sheet_title)

    A_DATA = yaml.safe_load(open(args.a_yaml))
    B_DATA = yaml.safe_load(open(args.b_yaml))
    FAM_LOOKUP = load_fam_lookup(FAM_LOOKUP)

    ibd_nodes_a = get_ibd_counts_from_dir(A_DATA["iba_gaf_path"], args.mods_only)
    ibd_nodes_b = get_ibd_counts_from_dir(B_DATA["iba_gaf_path"], args.mods_only)

    headers = [
        "{} family".format(A_DATA["data_title"]), 
        "{} family".format(B_DATA["data_title"]), 
        "PTN", 
        "term", 
        A_DATA["data_title"], 
        B_DATA["data_title"]
    ]
    # print("\t".join(headers))
    writer.writerow(headers)
    sheet.append_row(headers)
    
    affected_ptns = set()
    for n in ibd_nodes_a:
        for term in ibd_nodes_a[n]:
            a_term_count = query_ds_by_ptn_and_term(ibd_nodes_a, n, term)
            # Now check B to see if entry for same PTN and term
            family_b, b_term_count = None, None
            if n in ibd_nodes_b and term in ibd_nodes_b[n]:
                b_term_count = query_ds_by_ptn_and_term(ibd_nodes_b, n, term)
            # Only print if A != B? Maybe don't care about non-changes?
            if (a_term_count != b_term_count and b_term_count is not None) or b_term_count is None:
                family_a = get_family_for_ptn(n, A_DATA["classification_version_sid"])
                family_b = get_family_for_ptn(n, B_DATA["classification_version_sid"])
                row_vals = [family_a, family_b, n, term, a_term_count, b_term_count]
                # print(row_vals)
                writer.writerow(row_vals)
                sheet.append_row(row_vals)
                affected_ptns.add(n)

    # After A is exhaustively checked, go through B, skipping entries where already matching A by node AND term.
    for n in ibd_nodes_b:
        family_b = get_family_for_ptn(n, B_DATA["classification_version_sid"])
        for term in ibd_nodes_b[n]:
            if n in ibd_nodes_a and term in ibd_nodes_a[n]:
                # Skip because this already should be handled in A above
                continue
            else:
                b_term_count = query_ds_by_ptn_and_term(ibd_nodes_b, n, term)
                row_vals = [None, family_b, n, term, None, b_term_count]
                # print(row_vals)
                writer.writerow(row_vals)
                sheet.append_row(row_vals)
                affected_ptns.add(n)

    # For now, only concerned with producing full (not MOD-filtered) list of affected IBAs
    if not args.mods_only:
        # Construct A and B GAFs for only affected PTNs
        base_path = A_DATA["iba_gaf_path"].replace("/IBA_GAFs", "")
        with open("{}/affected_ibas.gaf".format(base_path), "w") as gaf_a:
            gaf_a.writelines(get_iba_gafs_by_ibd_ptn_list(affected_ptns, A_DATA["iba_gaf_path"], args.mods_only))

        base_path = B_DATA["iba_gaf_path"].replace("/IBA_GAFs", "")
        with open("{}/affected_ibas.gaf".format(base_path), "w") as gaf_b:
            gaf_b.writelines(get_iba_gafs_by_ibd_ptn_list(affected_ptns, B_DATA["iba_gaf_path"], args.mods_only))

    outf.close()
    handler.publish_sheet(sheet)
