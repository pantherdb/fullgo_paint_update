-- need to find all ancestor nodes for a paint annotated node annotated in paint_annotation_new with evidence type 47 (PAINT_ANCESTOR), if ancestor paint_annotation_new with the same term exists, insert it as paint_evidence, keep the paint_annotation_new, if not, obsolete paint_annotation_new
-- insert into paint_evidence_fix table, the non-obsolete ancestor paint_annotation_new id with the same go terms for its child paint_annotation_new with evidence type 47
set search_path = 'panther_upl';
insert into paint_evidence_fix (
            evidence_id, evidence_type_sid, classification_id, primary_object_id, 
            evidence, is_editable, created_by, creation_date, obsoleted_by, 
            obsolescence_date, updated_by, update_date, pathway_curation_id, 
            confidence_code_sid, annotation_id, protein_classification_id)
select nextval('uids'), 47, null, null, x.ancestor_paint_annotation_id, null, 1, now(), null, null, null, null, null, x.confidence_code_sid, x.child_paint_annotation_id, null
from
(
  select distinct pan.annotation_id child_paint_annotation_id, pan1.annotation_id ancestor_paint_annotation_id, pe.confidence_code_sid
  from
  (
    select child_node_acc, unnest(string_to_array(ancestor_node_acc, ',')) as ancestor from node_all_ancestors
  ) ca, paint_annotation_fix pan, node n, node n1, paint_annotation_fix pan1, paint_evidence_new pe
  where pan.node_id = n.node_id
  and n.accession = ca.child_node_acc
  and n1.node_id = pan1.node_id
  and n1.accession = ca.ancestor
  and pan.classification_id = pan1.classification_id
  and pan1.obsolescence_date is null
  and pan.annotation_id = pe.annotation_id
  and pe.evidence_type_sid = 47
  and n.classification_version_sid = 24
  and n1.classification_version_sid = 24
) x;

-- keep the old created_by and creation_date value for the same paint_evidence
set search_path = 'panther_upl';
update paint_evidence_fix pen
set created_by = pe.created_by, creation_date = pe.creation_date
from paint_evidence_new pe
where pen.annotation_id = pe.annotation_id
and pen.evidence = pe.evidence
and pen.evidence_type_sid = pe.evidence_type_sid
and pe.evidence_type_sid = 47;

-- Go through the paint_annotation_fix table, and see if an non-obsolete annotation_id (with evidence_type as paint_ancestor (47) only) is in the paint_evidence_fix table, if not, obsolete the paint_annotation_new entry
set search_path=panther_upl;
update paint_annotation_fix pan
set obsoleted_by = 1, obsolescence_date = now()
from paint_evidence_new pe
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 47
and pan.annotation_id not in (select annotation_id from paint_evidence_fix where evidence_type_sid = 47)
and pan.obsolescence_date is null;

-- Go through the paint_annotation_fix table, and see if an obsoleted (by user 1) annotation_id (with evidence_type as paint_ancestor (47) only) is in the paint_evidence_fix table, if yes, un-obsolete the paint_annotation_new entry
set search_path=panther_upl;
update paint_annotation_fix pan
set obsoleted_by = null, obsolescence_date = null
from paint_evidence_new pe
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 47
and pan.annotation_id in (select annotation_id from paint_evidence_fix where evidence_type_sid = 47)
and pan.obsolescence_date is not null
and pan.obsoleted_by = 1;