import csv
import os
from pthr_db_caller.db_caller import DBCaller

# Diff lookups for versions?
FAM_LOOKUP = {}
# Data model
# FAM_LOOKUP = {
#     "PTN12345678": {
#         24: "PTHR14567",
#         26: "PTHR14567",
#     }
# }

# A/B comparison data needed:
# 13.1
a_data = {
    "data_title": "PTHR 13.1",
    "classification_version_sid": 24,
    "table_name_suffix": "_v13_1", # not really needed for this
    "iba_gaf_path": "2019-06-17_fullgo_13_1/IBA_GAFs"
}
# 14.1
b_data = {
    "data_title": "PTHR 14.1",
    "classification_version_sid": 26,
    "table_name_suffix": "", # not really needed for this
    "iba_gaf_path": "2019-06-17_fullgo_14_1/IBA_GAFs"
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
def get_ibd_counts_from_dir(dir_path):
    ibd_nodes = {}
    for gaf in os.listdir(dir_path):
        gaf_f = open("{}/{}".format(dir_path, gaf))
        for l in gaf_f.readlines():
            if not l.startswith("!"):
                parts = l.split("\t")
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


caller = DBCaller()

def get_family_for_ptn_from_db(node_ptn, cls_ver_id):
    # Call DB
    query = """
    select split_part(n.accession,':',1) from panther_upl.node n where n.classification_version_sid = {} and n.public_id = '{}';
    """.format(cls_ver_id, node_ptn)
    results = caller.run_cmd_line_args(query.rstrip(), no_header_footer=True)
    if len(results) > 1:  # Col header always included
        return results[1][0]


def get_family_for_ptn(node_ptn, cls_ver_id):
    cls_to_fams = FAM_LOOKUP.get(node_ptn)
    if cls_to_fams is None:
        family = get_family_for_ptn_from_db(node_ptn, cls_ver_id)  # This takes too long
        cls_to_fams = {cls_ver_id: family}
        FAM_LOOKUP[node_ptn] = cls_to_fams
        return family
    else:
        family = FAM_LOOKUP[node_ptn].get(cls_ver_id)
        if family is None:
            family = get_family_for_ptn_from_db(node_ptn, cls_ver_id)
            FAM_LOOKUP[node_ptn][cls_ver_id] = family
        return family


if __name__ == "__main__":
    outfile = "iba_count_diff.tsv"
    outf = open(outfile, "w+")
    writer = csv.writer(outf, delimiter="\t")

    ibd_nodes_a = get_ibd_counts_from_dir(a_data["iba_gaf_path"])
    ibd_nodes_b = get_ibd_counts_from_dir(b_data["iba_gaf_path"])

    headers = [
        "{} family".format(a_data["data_title"]), 
        "{} family".format(b_data["data_title"]), 
        "PTN", 
        "term", 
        a_data["data_title"], 
        b_data["data_title"]
    ]
    print("\t".join(headers))
    writer.writerow(headers)
    
    for n in ibd_nodes_a:
        family_a = get_family_for_ptn(n, a_data["classification_version_sid"])
        for term in ibd_nodes_a[n]:
            a_term_count = query_ds_by_ptn_and_term(ibd_nodes_a, n, term)
            # Now check B to see if entry for same PTN and term
            family_b, b_term_count = None, None
            if n in ibd_nodes_b and term in ibd_nodes_b[n]:
                family_b = get_family_for_ptn(n, b_data["classification_version_sid"])
                b_term_count = query_ds_by_ptn_and_term(ibd_nodes_b, n, term)
            row_vals = [family_a, family_b, n, term, a_term_count, b_term_count]
            try:
                print(row_vals)
                writer.writerow(row_vals)
            except:
                print(row_vals)
                print("\t".join(row_vals))
        break
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
                print(row_vals)
                writer.writerow(row_vals)
        break

    outf.close()
# Keep list of 

# Possible scenarios
# 1. IBD node in both A and B
#   Fun scenario:
# ibd_nodes_a = {
#     "PTN12345678": {
#         "GO:123456": 34,
#         "GO:456432": 10
#     }
# }
# ibd_nodes_b = {
#     "PTN12345678": {
#         "GO:123456": 34,
#     }
# }
# 2. IBD node in A only
# 3. IBD node in B only

# What if PTN col was for leaf PTN?
# - If GO term included, wouldn't count be 1 for each line?
# -- If yes, lose GO term. Maybe different report.