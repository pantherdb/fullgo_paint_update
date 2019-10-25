# Take list of IBD pairs (AN1 and AN2). AN2 will be obsoleted.
# Update all paint_evidences pointing to paint_annotations pointing to AN2, replace with paint_annotations pointing to AN1.
#   These paint_evidence's annotations should be IKR/IRDs. Are there any that are other?

# import os
# print(os.getcwd())
# import sys
# sys.path.append("scripts")

from pthr_db_caller.db_caller import DBCaller
from pthr_db_caller.panther_tree_graph import PantherTreeGraph
from pthr_db_caller.pthr_comment_helper import PthrCommentHelper
from pthr_db_caller.curation_status_model import PaintCurationStatusHelper
import csv
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('library_path')
parser.add_argument('table_suffix')
parser.add_argument('cachefile')

args = parser.parse_args()

# TABLE_SUFFIX = "_new"
# TABLE_SUFFIX = ""
TABLE_SUFFIX = args.table_suffix
# LIB_DIR = "/home/pmd-02/pdt/pdthomas/panther/famlib/rel/PANTHER14.1"  # HPC
# LIB_DIR = "resources/tree_files"  # local
LIB_DIR = args.library_path  # TODO: BuildConfig parameter?

CALLER = DBCaller()
COMMENT_HELPER = PthrCommentHelper(comments_tablename="comments{}".format(TABLE_SUFFIX), classification_version_sid=26)
CURATION_STATUS_HELPER = PaintCurationStatusHelper(curation_status_tablename="curation_status{}".format(TABLE_SUFFIX), classification_version_sid=26)

QUERY = """
select distinct split_part(na.accession, ':', 1) as family, paa.annotation_id anc_annotation_id, na.public_id ancestor_ptn, na.accession ancestor_an, pa.annotation_id desc_annotation_id, n.public_id descendant_ptn, n.accession descendant_an, gc.accession, gc.classification_id, q.qualifier
from panther_upl.paint_annotation{table_suffix} pa
join panther_upl.paint_evidence{table_suffix} pe on pe.annotation_id = pa.annotation_id
join panther_upl.node n on n.node_id = pa.node_id
join (select child_node_acc, unnest(string_to_array(ancestor_node_acc, ',')) as ancestor from panther_upl.node_all_ancestors_v14_1) naa on naa.child_node_acc = n.accession
join panther_upl.node na on na.accession = naa.ancestor
join panther_upl.paint_annotation{table_suffix} paa on paa.node_id = na.node_id and paa.classification_id = pa.classification_id
join panther_upl.paint_evidence{table_suffix} pea on pea.annotation_id = paa.annotation_id
join panther_upl.go_classification{table_suffix} gc on gc.classification_id = pa.classification_id
left join panther_upl.paint_annotation_qualifier{table_suffix} paq on paq.annotation_id = pa.annotation_id
left join panther_upl.paint_annotation_qualifier{table_suffix} paaq on paaq.annotation_id = paa.annotation_id
left join panther_upl.qualifier q on q.qualifier_id = paq.qualifier_id
where n.classification_version_sid = 26
and na.classification_version_sid = 26
and pa.obsolescence_date is null
and paa.obsolescence_date is null
and pe.confidence_code_sid = 15  -- IBD
and pea.confidence_code_sid = 15  -- IBD
and (paq.qualifier_id = paaq.qualifier_id or (paq.qualifier_id is null and paaq.qualifier_id is null));
""".format(table_suffix=TABLE_SUFFIX)

# cachefile = "resources/sql/cache/obsolete_redundant_ibds.txt"
ibd_results = CALLER.run_cmd_line_args(QUERY.rstrip(), no_header_footer=True, rows_outfile=args.cachefile)
red_ibds = ibd_results[1:]  # skip header row

# with open(cachefile) as rf:
#     reader = csv.reader(rf, delimiter=";")
#     red_ibds = []
#     next(reader)  # skip header row
#     for r in reader:
#         red_ibds.append(r)

def get_nodes_between(ancestor_an, descendant_an, family):
    # How about we try parsing tree files?
    tree_graph = PantherTreeGraph("{}/books/{}/tree.tree".format(LIB_DIR, family))  # HPC
    # tree_graph = PantherTreeGraph("{}/{}.tree".format(LIB_DIR, family))  # local
    return tree_graph.nodes_between(ancestor_an, descendant_an)

# btwn_nodes = get_nodes_between("PTN002469673", "PTN000031802", "PTHR10283")
# btwn_nodes = get_nodes_between("AN105", "AN107", family="PTHR10283")
# print(btwn_nodes)

comments_for_fam = {}
def add_comment(comments_dict : dict, family, comment):
    if family not in comments_dict:
        comments_dict[family] = []
    if comment not in comments_dict[family]:
        comments_dict[family].append(comment)
    return comments_dict

# TODO: Run query for redundant IBDs on same node and term. Figure out which annots to obsolete and pass list of vals into red_ibds.
# example = [family, good_ibd_annot_id, good_ibd_ptn, good_ibd_an, bad_ibd_annot_id, bad_ibd_ptn, bad_ibd_an, term, term_id, qualifier]
REDUNDANT_SAME_NODE_IBDS = """
select n.public_id, gc.accession, redundant_annots.* from
(
	select pa.node_id, pa.classification_id, pe2.confidence_code, q.qualifier, count(*) from paint_annotation pa
	join (select distinct cc.confidence_code, pe.annotation_id from paint_evidence pe 
		join confidence_code cc on cc.confidence_code_sid = pe.confidence_code_sid
		where pe.obsolescence_date is null
	) pe2 on pe2.annotation_id = pa.annotation_id
	left join paint_annotation_qualifier paq on paq.annotation_id = pa.annotation_id
	left join qualifier q on q.qualifier_id = paq.qualifier_id
	where pa.obsolescence_date is null
	group by pa.node_id, pa.classification_id, pe2.confidence_code, q.qualifier having count(*) > 1
) redundant_annots
join node n on n.node_id = redundant_annots.node_id
join go_classification gc on gc.classification_id = redundant_annots.classification_id;
"""

have_nots = {}
evs_to_update = {}
ibds_to_obsolete = {}
# Got list of IBDs to obsolete
for ibd in red_ibds:
    family = ibd[0]
    anc_annotation_id = ibd[1]
    anc_ptn = ibd[2]
    anc_an = ibd[3]
    desc_annotation_id = ibd[4]
    desc_ptn = ibd[5]
    desc_an = ibd[6]
    term = ibd[7]
    term_id = ibd[8]
    qualifier = ibd[9]

    # Check for NOT IKR/IRD to same term in-between anc and desc nodes. If found, don't obsolete descendant IBD.
    between_nodes = get_nodes_between(anc_an.split(":")[1], desc_an.split(":")[1], family=family)
    if len(between_nodes) > 0:
        query_node_list = []
        for n in between_nodes:
            query_node_list.append(":".join([family, n]))

        # pe.evidence_type_sid = 47 PAINT_ANCESTOR; pe.confidence_code_sid = 17 IRD
        not_query = """
            select pa.annotation_id from panther_upl.paint_annotation{table_suffix} pa
            join panther_upl.paint_evidence{table_suffix} pe on pe.annotation_id = pa.annotation_id
            join panther_upl.node n on n.node_id = pa.node_id
            where n.classification_version_sid = 26
            and pa.classification_id = {classification_id}
            and pe.evidence_type_sid = 47
            and pe.confidence_code_sid = 17
            and n.accession in ('{nodes}');
        """.format(table_suffix=TABLE_SUFFIX, classification_id=term_id, nodes="','".join(query_node_list))

        not_results = CALLER.run_cmd_line_args(not_query.rstrip(), no_header_footer=True)
        if len(not_results) > 1:
            if family not in have_nots:
                have_nots[family] = []
            for r in not_results[1:]:
                have_nots[family].append(r[0])
            # Skip obsoletion of this IBD
            continue

    # If OK to obsolete IBD, update any paint_evidence record that references it
    ev_query = """
        select pe.evidence_id, n.public_id, cc.confidence_code from panther_upl.paint_evidence{table_suffix} pe
        join panther_upl.paint_annotation{table_suffix} pa on pa.annotation_id = pe.annotation_id
        join panther_upl.node n on n.node_id = pa.node_id
        join panther_upl.confidence_code cc on cc.confidence_code_sid = pe.confidence_code_sid
        where pe.obsolescence_date is null
        and pe.evidence = '{annotation_id}';
    """.format(table_suffix=TABLE_SUFFIX, annotation_id=desc_annotation_id)

    results = CALLER.run_cmd_line_args(ev_query.rstrip(), no_header_footer=True)
    if len(results) > 1:
        # Gonna need to update these evidence records with evidence=anc_annotation_id
        if family not in evs_to_update:
            evs_to_update[family] = []
        for r in results[1:]:
            # Construct comment here
            ev_id = r[0]
            changed_ptn = r[1]
            conf_code = r[2]
            comment = "Evidence PTN for {conf_code} {term} annotation to {changed_ptn} changed from {desc_ptn} to {anc_ptn} due to {desc_ptn}s {term} annotation being marked redundant and thus obsoleted.".format(
                    conf_code=conf_code,
                    term=term,
                    changed_ptn=changed_ptn,
                    desc_ptn=desc_ptn,
                    anc_ptn=anc_ptn
            )
            comments_for_fam = add_comment(comments_for_fam, family, comment)

            change_evidence_query = """
                update panther_upl.paint_evidence{table_suffix}
                set evidence = '{anc_annotation_id}'
                where evidence_id = {ev_id};
            """.format(table_suffix=TABLE_SUFFIX, anc_annotation_id=anc_annotation_id, ev_id=ev_id)

            CALLER.run_cmd_line_args(change_evidence_query.rstrip(), no_header_footer=True)

    # Obsolete desc_annotation using desc_annotation_id. Both paint_annotation and paint_evidence.
    update_annot_query = """
        update panther_upl.paint_annotation{table_suffix}
        set obsoleted_by = 1, obsolescence_date = now()
        where annotation_id = {annotation_id};
    """.format(table_suffix=TABLE_SUFFIX, annotation_id=desc_annotation_id)
    update_evidence_query = """
        update panther_upl.paint_evidence{table_suffix}
        set obsoleted_by = 1, obsolescence_date = now()
        where annotation_id = {annotation_id};
    """.format(table_suffix=TABLE_SUFFIX, annotation_id=desc_annotation_id)

    CALLER.run_cmd_line_args(update_annot_query.rstrip(), no_header_footer=True)
    CALLER.run_cmd_line_args(update_evidence_query.rstrip(), no_header_footer=True)

    # Add comment about redundant IBD obsoletion.
    # Convoluted method of preventing extra space if qualifier is NULL
    comment_bits = ["Annotation of"]
    if qualifier and len(qualifier) > 0:
        comment_bits.append(qualifier)
    comment_bits.append("{term} to {desc_ptn} was obsoleted because its ancestor {anc_ptn} has the same annotation.".format(
            term=term,
            desc_ptn=desc_ptn,
            anc_ptn=anc_ptn
        )
    )
    comment_about_obs = " ".join(comment_bits)
    comments_for_fam = add_comment(comments_for_fam, family, comment_about_obs)

for fam in comments_for_fam:
    cmt_text = "\n".join(comments_for_fam[fam])
    COMMENT_HELPER.update_or_insert_comment(family_id=fam, comment_text=cmt_text)
    CURATION_STATUS_HELPER.insert_curation_status(fam, 7)  # 7 = require paint review
    # print(cmt_text)

print(have_nots)
# print(evs_to_update)
# {'PTHR11451': [Decimal('88231633')]}
# {'PTHR10336': [909054683, 88218457], 'PTHR12628': [730102247, 730102376], 'PTHR19241': [909054708, 909054710, 909054712, 909054714, 909054716, 909054718, 909054720, 909054722, 909054724, 909054726]}
