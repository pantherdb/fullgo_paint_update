-- insert into paint_evidence_fix table, evidence of the leaf go_annotation (with experimental confidence code) with the same go terms for 
-- every paint_annotation_new with evidence type 46 (paint_exp)

set search_path = 'panther_upl';
ALTER TABLE paint_evidence_old RENAME TO paint_evidence_fix;
truncate table paint_evidence_fix;
insert into paint_evidence_fix (
            evidence_id, evidence_type_sid, classification_id, primary_object_id, 
            evidence, is_editable, created_by, creation_date, obsoleted_by, 
            obsolescence_date, updated_by, update_date, pathway_curation_id, 
            confidence_code_sid, annotation_id, protein_classification_id)
select nextval('uids'), 46, null, null, x.go_annotation_id, null, 1, now(), null, null, null, null, null, x.confidence_code_sid, x.paint_annotation_id, null
from
(select distinct ga.annotation_id go_annotation_id, pa.annotation_id paint_annotation_id, pe.confidence_code_sid
from
(select parent_node_acc, unnest(string_to_array(child_leaf_node_acc, ',')) as leaf from node_all_leaves) pl, paint_annotation_new pa, node n, node n1, go_annotation ga, go_evidence ge, confidence_code cc, paint_evidence_new pe
where pa.node_id = n.node_id
and n.accession = pl.parent_node_acc
and n1.node_id = ga.node_id
and n1.accession = pl.leaf
and pa.classification_id = ga.classification_id
and pa.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 46
and n.classification_version_sid = 24
and n1.classification_version_sid = 24
and ga.annotation_id = ge.annotation_id
and ge.confidence_code_sid = cc.confidence_code_sid
and cc.confidence_code in ('EXP', 'IDA', 'IPI', 'IMP', 'IGI', 'IEP', 'HTP', 'HDA', 'HMP', 'HGI', 'HEP')) x;

-- keep the old created_by and creation_date value for the same paint_evidence
set search_path = 'panther_upl';
update paint_evidence_fix pen
set created_by = pe.created_by, creation_date = pe.creation_date
from paint_evidence_new pe
where pen.annotation_id = pe.annotation_id
and pen.evidence = pe.evidence
and pen.evidence_type_sid = pe.evidence_type_sid;

-- Go through the paint_annotation_fix table (replicate of paint_annotation_new table for update, original table as a backup), and see if an annotation_id (for paint_annotation_new of evidence_type paint_exp (46) only) is in the paint_evidence_fix table, if not, obsolete the paint_annotation_new entry
set search_path=panther_upl;
ALTER TABLE paint_annotation_old RENAME TO paint_annotation_fix;
truncate table paint_annotation_fix;
insert into paint_annotation_fix
select * from paint_annotation_new;

set search_path=panther_upl;
update paint_annotation_fix pan
set obsoleted_by = 1, obsolescence_date = now()
from paint_evidence_new pe
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 46
and pan.annotation_id not in (select annotation_id from paint_evidence_fix where evidence_type_sid = 46)
and pan.obsolescence_date is null;

-- Go through the paint_annotation_fix table, and see if an previously obsoleted (by user , PANTHERLOAD) annotation_id (for paint_annotation_new with evidence_type as paint_exp (46) only) is in the paint_evidence_fix table, if yes, un-obsolete the paint_annotation_new entry
set search_path=panther_upl;
update paint_annotation_fix pan
set obsoleted_by = null, obsolescence_date = null
from paint_evidence_new pe
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 46
and pan.annotation_id in (select annotation_id from paint_evidence_fix where evidence_type_sid = 46)
and pan.obsolescence_date is not null
and pan.obsoleted_by = 1;