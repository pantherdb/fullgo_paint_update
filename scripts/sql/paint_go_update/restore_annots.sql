-- insert into paint_evidence_fix table, evidence of the leaf go_annotation (with experimental confidence code) with the same go terms for 
-- every paint_annotation_new with evidence type 46 (paint_exp)

set search_path = 'panther_upl';
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
and cc.confidence_code in ('EXP', 'IDA', 'IPI', 'IMP', 'IGI', 'IEP')) x;

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
truncate paint_annotation_fix;
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

-- insert a row with the status 'require paint review' for panther families that obsoleted paint_annotation_new due to above method into the curation_status_new ( a replicate of curation_status table for update).
set search_path = panther_upl;
INSERT INTO curation_status_new(
            curation_status_id, status_type_sid, classification_id, user_id, 
            creation_date)
SELECT nextval('uids'), 7, X.classification_id, 1113, now()
from (SELECT distinct cls.classification_id
from paint_evidence_new pe, paint_annotation_fix pan, node n, classification cls, paint_annotation_new pa
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 46
and not exists (select 1 from paint_evidence_fix pen where pan.annotation_id = pen.annotation_id and pen.evidence_type_sid = 46)
and pan.annotation_id = pa.annotation_id
and pa.obsolescence_date is null
and pan.node_id = n.node_id
and n.classification_version_sid = 24
and split_part(n.accession,':',1)=cls.accession
and cls.classification_version_sid = 24
and cls.depth = 5) X;

-- insert a row with the status 'require paint review' for panther families that un-obsoleted paint_annotation_new due to above method into the curation_status_new ( a replicate of curation_status table for update). 
set search_path = panther_upl;
INSERT INTO curation_status_new(
            curation_status_id, status_type_sid, classification_id, user_id, 
            creation_date)
SELECT nextval('uids'), 7, X.classification_id, 1113, now()
from (SELECT distinct cls.classification_id
from paint_evidence_new pe, paint_annotation_fix pan, node n, classification cls, paint_annotation_new pa
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 46
and exists (select 1 from paint_evidence_fix pen where pan.annotation_id = pen.annotation_id and pen.evidence_type_sid = 46)
and pan.annotation_id = pa.annotation_id
and pa.obsolescence_date is not null
and pa.obsoleted_by = 1
and pan.node_id = n.node_id
and n.classification_version_sid = 24
and split_part(n.accession,':',1)=cls.accession
and cls.classification_version_sid = 24
and cls.depth = 5) X;

-- update the comments_new table (a replicate of comments table for update)
set search_path = panther_upl;
update comments_new cm
set remark = cm.remark || '\n' || current_date || ': PAINT_EXP annotation to node ' || x.public_id || ' with ' || x.go_term || ' was obsoleted because there was no supporting leaf node experimental go annotation left after PANTHER library version update.\n'
from (SELECT distinct cls.classification_id, n.public_id, gc.accession go_term
from paint_evidence_new pe, paint_annotation_fix pan, node n, classification cls, go_classification gc, paint_annotation_new pa
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 46
and not exists (select 1 from paint_evidence_fix pen where pan.annotation_id = pen.annotation_id and pen.evidence_type_sid = 46)
and pan.annotation_id = pa.annotation_id
and pa.obsolescence_date is null
and pan.node_id = n.node_id
and n.classification_version_sid = 24
and split_part(n.accession,':',1)=cls.accession
and cls.classification_version_sid = 24
and cls.depth = 5
and pan.classification_id = gc.classification_id) x
where cm.classification_id = x.classification_id;

set search_path = panther_upl;
insert into comments_new (comment_id, classification_id, protein_id, remark, created_by, 
            creation_date, obsoleted_by, obsolescence_date, node_id)
select nextval('uids'), x.classification_id, null, current_date || ': PAINT_EXP annotation to node ' || x.public_id || ' with ' || x.go_term || ' was obsoleted because there was no supporting leaf node experimental go annotation left after PANTHER library version update.\n', 1113, current_date, null, null, null
from (SELECT distinct cls.classification_id, n.public_id, gc.accession go_term
from paint_evidence_new pe, paint_annotation_fix pan, node n, classification cls, go_classification gc, paint_annotation_new pa
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 46
and not exists (select 1 from paint_evidence_fix pen where pan.annotation_id = pen.annotation_id and pen.evidence_type_sid = 46)
and pan.annotation_id = pa.annotation_id
and pa.obsolescence_date is null
and pan.node_id = n.node_id
and n.classification_version_sid = 24
and split_part(n.accession,':',1)=cls.accession
and cls.classification_version_sid = 24
and cls.depth = 5
and pan.classification_id = gc.classification_id) x
where not exists (
select 1 from comments_new cm
where cm.classification_id = x.classification_id);

set search_path = panther_upl;
update comments_new cm
set remark = cm.remark || '\n' || current_date || ': PAINT_EXP annotation to node ' || x.public_id || ' with ' || x.go_term || ' was un-obsoleted because there now exists new supporting leaf node experimental go annotation after PANTHER library version update.\n'
from (SELECT distinct cls.classification_id, n.public_id, gc.accession go_term
from paint_evidence_new pe, paint_annotation_fix pan, node n, classification cls, go_classification gc, paint_annotation_new pa
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 46
and exists (select 1 from paint_evidence_fix pen where pan.annotation_id = pen.annotation_id and pen.evidence_type_sid = 46)
and pan.annotation_id = pa.annotation_id
and pa.obsolescence_date is not null
and pa.obsoleted_by = 1
and pan.node_id = n.node_id
and n.classification_version_sid = 24
and split_part(n.accession,':',1)=cls.accession
and cls.classification_version_sid = 24
and cls.depth = 5
and pan.classification_id = gc.classification_id) x
where cm.classification_id = x.classification_id;

set search_path = panther_upl;
insert into comments_new (comment_id, classification_id, protein_id, remark, created_by, 
            creation_date, obsoleted_by, obsolescence_date, node_id)
select nextval('uids'), x.classification_id, null, current_date || ': PAINT_EXP annotation to node ' || x.public_id || ' with ' || x.go_term || ' was un-obsoleted because there now exists new supporting leaf node experimental go annotation after PANTHER library version update.\n', 1113, current_date, null, null, null
from (SELECT distinct cls.classification_id, n.public_id, gc.accession go_term
from paint_evidence_new pe, paint_annotation_fix pan, node n, classification cls, go_classification gc, paint_annotation_new pa
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 46
and exists (select 1 from paint_evidence_fix pen where pan.annotation_id = pen.annotation_id and pen.evidence_type_sid = 46)
and pan.annotation_id = pa.annotation_id
and pa.obsolescence_date is not null
and pa.obsoleted_by = 1
and pan.node_id = n.node_id
and n.classification_version_sid = 24
and split_part(n.accession,':',1)=cls.accession
and cls.classification_version_sid = 24
and cls.depth = 5
and pan.classification_id = gc.classification_id) x
where not exists (
select 1 from comments_new cm
where cm.classification_id = x.classification_id);

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

-- insert a row with the status 'require paint review' for panther families that obsoleted paint_annotation_new due to above method into the curation_status_new. 
set search_path = panther_upl;
INSERT INTO curation_status_new(
            curation_status_id, status_type_sid, classification_id, user_id, 
            creation_date)
SELECT nextval('uids'), 7, X.classification_id, 1113, now()
from (SELECT distinct cls.classification_id
from paint_evidence_new pe, paint_annotation_fix pan, node n, classification cls, paint_annotation_new pa
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 47
and not exists (select 1 from paint_evidence_fix pen where pan.annotation_id = pen.annotation_id and pen.evidence_type_sid = 47)
and pan.annotation_id = pa.annotation_id
and pa.obsolescence_date is null
and pan.node_id = n.node_id
and n.classification_version_sid = 24
and split_part(n.accession,':',1)=cls.accession
and cls.classification_version_sid = 24
and cls.depth = 5) X;

-- insert a row with the status 'require paint review' for panther families that un-obsoleted paint_annotation_new due to above method into the curation_status_new.  
set search_path = panther_upl;
INSERT INTO curation_status_new(
            curation_status_id, status_type_sid, classification_id, user_id, 
            creation_date)
SELECT nextval('uids'), 7, X.classification_id, 1113, now()
from (SELECT distinct cls.classification_id
from paint_evidence_new pe, paint_annotation_fix pan, node n, classification cls, paint_annotation_new pa
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 47
and exists (select 1 from paint_evidence_fix pen where pan.annotation_id = pen.annotation_id and pen.evidence_type_sid = 47)
and pan.annotation_id = pa.annotation_id
and pa.obsolescence_date is not null
and pa.obsoleted_by = 1
and pan.node_id = n.node_id
and n.classification_version_sid = 24
and split_part(n.accession,':',1)=cls.accession
and cls.classification_version_sid = 24
and cls.depth = 5) X;

-- update comments_new table
set search_path = panther_upl;
update comments_new cm
set remark = cm.remark || '\n' || current_date || ': PAINT_ANCESTOR annotation to node ' || x.public_id || ' with ' || x.go_term || ' was obsoleted because there was no supporting ancesotr node paint annotation left after PANTHER library version update.\n'
from (SELECT distinct cls.classification_id, n.public_id, gc.accession go_term
from paint_evidence_new pe, paint_annotation_fix pan, node n, classification cls, go_classification gc, paint_annotation_new pa
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 47
and not exists (select 1 from paint_evidence_fix pen where pan.annotation_id = pen.annotation_id and pen.evidence_type_sid = 47)
and pan.annotation_id = pa.annotation_id
and pa.obsolescence_date is null
and pan.node_id = n.node_id
and n.classification_version_sid = 24
and split_part(n.accession,':',1)=cls.accession
and cls.classification_version_sid = 24
and cls.depth = 5
and pan.classification_id = gc.classification_id) x
where cm.classification_id = x.classification_id;

set search_path = panther_upl;
insert into comments_new (comment_id, classification_id, protein_id, remark, created_by, 
            creation_date, obsoleted_by, obsolescence_date, node_id)
select nextval('uids'), x.classification_id, null, current_date || ': PAINT_EXP annotation to node ' || x.public_id || ' with ' || x.go_term || ' was obsoleted because there was no supporting leaf node experimental go annotation left after PANTHER library version update.\n', 1113, current_date, null, null, null
from (SELECT distinct cls.classification_id, n.public_id, gc.accession go_term
from paint_evidence_new pe, paint_annotation_fix pan, node n, classification cls, go_classification gc, paint_annotation_new pa
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 47
and not exists (select 1 from paint_evidence_fix pen where pan.annotation_id = pen.annotation_id and pen.evidence_type_sid = 47)
and pan.annotation_id = pa.annotation_id
and pa.obsolescence_date is null
and pan.node_id = n.node_id
and n.classification_version_sid = 24
and split_part(n.accession,':',1)=cls.accession
and cls.classification_version_sid = 24
and cls.depth = 5
and pan.classification_id = gc.classification_id) x
where not exists (
select 1 from comments_new cm
where cm.classification_id = x.classification_id);

set search_path = panther_upl;
update comments_new cm
set remark = cm.remark || '\n' || current_date || ': PAINT_ANCESTOR annotation to node ' || x.public_id || ' with ' || x.go_term || ' was un-obsoleted because there exists now supporting ancesotr node paint annotation after PANTHER library version update.\n'
from (SELECT distinct cls.classification_id, n.public_id, gc.accession go_term
from paint_evidence_new pe, paint_annotation_fix pan, node n, classification cls, go_classification gc, paint_annotation_new pa
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 47
and exists (select 1 from paint_evidence_fix pen where pan.annotation_id = pen.annotation_id and pen.evidence_type_sid = 47)
and pan.annotation_id = pa.annotation_id
and pa.obsolescence_date is not null
and pa.obsoleted_by = 1
and pan.node_id = n.node_id
and n.classification_version_sid = 24
and split_part(n.accession,':',1)=cls.accession
and cls.classification_version_sid = 24
and cls.depth = 5
and pan.classification_id = gc.classification_id) x
where cm.classification_id = x.classification_id;

set search_path = panther_upl;
insert into comments_new (comment_id, classification_id, protein_id, remark, created_by, 
            creation_date, obsoleted_by, obsolescence_date, node_id)
select nextval('uids'), x.classification_id, null, current_date || ': PAINT_EXP annotation to node ' || x.public_id || ' with ' || x.go_term || ' was un-obsoleted because there exists now supporting leaf node experimental go annotation after PANTHER library version update.\n', 1113, current_date, null, null, null
from (SELECT distinct cls.classification_id, n.public_id, gc.accession go_term
from paint_evidence_new pe, paint_annotation_fix pan, node n, classification cls, go_classification gc, paint_annotation_new pa
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 47
and exists (select 1 from paint_evidence_fix pen where pan.annotation_id = pen.annotation_id and pen.evidence_type_sid = 47)
and pan.annotation_id = pa.annotation_id
and pa.obsolescence_date is not null
and pa.obsoleted_by = 1
and pan.node_id = n.node_id
and n.classification_version_sid = 24
and split_part(n.accession,':',1)=cls.accession
and cls.classification_version_sid = 24
and cls.depth = 5
and pan.classification_id = gc.classification_id) x
where not exists (
select 1 from comments_new cm
where cm.classification_id = x.classification_id);

-- insert into paint_evidence_fix tables with other paint_evidence_new table rows (with evidence_type other than 46 and 47)
set search_path = panther_upl;
insert into paint_evidence_fix
select * from paint_evidence_new
where evidence_type_sid not in (46, 47);

-- insert obsoleted type 46 and 47 evidence that not in paint_evidence_fix table into the paint_evidence_fix table, keep them obsoleted, just as a record
set search_path = panther_upl;
insert into paint_evidence_fix
select * from paint_evidence_new pe
where pe.evidence_type_sid in (46, 47)
and pe.obsolescence_date is not null
and not exists (select 1 from paint_evidence_fix pen where pe.evidence = pen.evidence and pe.annotation_id = pen.annotation_id and pe.evidence_type_sid = pen.evidence_type_sid);

-- insert non-obsoleted type 46 and 47 evidence that not in paint_evidence_fix table into the paint_evidence_fix table, make them obsoleted, just as a record for backup
set search_path = panther_upl;
insert into paint_evidence_fix (
            evidence_id, evidence_type_sid, classification_id, primary_object_id, 
            evidence, is_editable, created_by, creation_date, obsoleted_by, 
            obsolescence_date, updated_by, update_date, pathway_curation_id, 
            confidence_code_sid, annotation_id, protein_classification_id)
select evidence_id, evidence_type_sid, classification_id, primary_object_id, 
            evidence, is_editable, created_by, creation_date, 1, 
            now(), updated_by, update_date, pathway_curation_id, 
            confidence_code_sid, annotation_id, protein_classification_id
from (select * from paint_evidence_new pe
where pe.evidence_type_sid in (46, 47)
and pe.obsolescence_date is null
and not exists (select 1 from paint_evidence_fix pen where pe.evidence = pen.evidence and pe.annotation_id = pen.annotation_id and pe.evidence_type_sid = pen.evidence_type_sid)) x;