import csv
import os
import datetime
import argparse
from util.publish_google_sheet import SheetPublishHandler, Sheet

parser = argparse.ArgumentParser()
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

MOD_ORGS = [
    "taxon:3702",	    # arabidopsis
    "taxon:6239",	    # nematode_worm
    "taxon:7955",	    # zebrafish
    "taxon:44689",	    # dictyostelium
    "taxon:7227",	    # fruit_fly
    "taxon:227321",	    # aspergillus
    "taxon:83333",	    # e_coli
    "taxon:9031",	    # chicken
    "taxon:10090",	    # mouse
    "taxon:10116",      # rat
    "taxon:559292",	    # budding_yeast
    "taxon:284812"	    # fission_yeast
]

# A/B comparison data needed:
# 13.1
a_data = {
    "data_title": "PTHR 13.1",
    "classification_version_sid": 24,
    "table_name_suffix": "_v13_1", # not really needed for this
    "iba_gaf_path": "2019-06-17_fullgo_13_1/IBA_GAFs",
    "node_dat_path": "/home/pmd-02/pdt/pdthomas/panther/xiaosonh/UPL/PANTHER13.1/library_building/DBload/node.dat"
}
# 14.1
b_data = {
    "data_title": "PTHR 14.1",
    "classification_version_sid": 26,
    "table_name_suffix": "", # not really needed for this
    "iba_gaf_path": "2019-06-17_fullgo_14_1/IBA_GAFs",
    "node_dat_path": "/auto/rcf-proj/hm/debert/PANTHER14.1/library_building/DBload/node.dat"
}

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



# def get_family_for_ptn_from_db(node_ptn, cls_ver_id):
#     # Call DB
#     query = """
#     select split_part(n.accession,':',1) from panther_upl.node n where n.classification_version_sid = {} and n.public_id = '{}';
#     """.format(cls_ver_id, node_ptn)
#     results = caller.run_cmd_line_args(query.rstrip(), no_header_footer=True)
#     if len(results) > 1:  # Col header always included
#         return results[1][0]

# def get_family_for_ptn_from_file(node_ptn, node_dat_path):
#     # Grep file? Nah.
#     # cmd = "grep {node_ptn} {node_dat_path} | cut -f1 | cut -d \":\" -f1".format(node_ptn=node_ptn, node_dat_path=node_dat_path)
#     # PTHR28113:AN0   PTN001999359    ROOT    SPECIATION      0
#     looku



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
    lookup = parse_and_load_node(lookup, a_data["classification_version_sid"], a_data["node_dat_path"])
    if a_data["node_dat_path"] == b_data["node_dat_path"]:
        lookup[b_data["classification_version_sid"]] = lookup[a_data["classification_version_sid"]]
    else:
        lookup = parse_and_load_node(lookup, b_data["classification_version_sid"], b_data["node_dat_path"])
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

    FAM_LOOKUP = load_fam_lookup(FAM_LOOKUP)

    ibd_nodes_a = get_ibd_counts_from_dir(a_data["iba_gaf_path"], args.mods_only)
    ibd_nodes_b = get_ibd_counts_from_dir(b_data["iba_gaf_path"], args.mods_only)

    headers = [
        "{} family".format(a_data["data_title"]), 
        "{} family".format(b_data["data_title"]), 
        "PTN", 
        "term", 
        a_data["data_title"], 
        b_data["data_title"]
    ]
    # print("\t".join(headers))
    writer.writerow(headers)
    sheet.append_row(headers)
    
    for n in ibd_nodes_a:
        for term in ibd_nodes_a[n]:
            a_term_count = query_ds_by_ptn_and_term(ibd_nodes_a, n, term)
            # Now check B to see if entry for same PTN and term
            family_b, b_term_count = None, None
            if n in ibd_nodes_b and term in ibd_nodes_b[n]:
                b_term_count = query_ds_by_ptn_and_term(ibd_nodes_b, n, term)
            # Only print if A != B? Maybe don't care about non-changes?
            if (a_term_count != b_term_count and b_term_count is not None) or b_term_count is None:
                family_a = get_family_for_ptn(n, a_data["classification_version_sid"])
                family_b = get_family_for_ptn(n, b_data["classification_version_sid"])
                row_vals = [family_a, family_b, n, term, a_term_count, b_term_count]
                # print(row_vals)
                writer.writerow(row_vals)
                sheet.append_row(row_vals)

    # After A is exhaustively checked, go through B, skipping entries where already matching A by node AND term.
    for n in ibd_nodes_b:
        family_b = get_family_for_ptn(n, b_data["classification_version_sid"])
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

    outf.close()
    handler.publish_sheet(sheet)
