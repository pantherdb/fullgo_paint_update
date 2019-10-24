-- 1.	The GO ID is no longer the primary ID in the obo file.
---- a.	The GO ID is obsoleted
------ i.	Has tag “replaced_by” field. Replace it with the ID and new term as suggested. Mark the family as “Require paint review”. In the comments table, record the obsoleted and new terms (both GO ID and name), and also the PTN IDs. 

-- find the panther families that have nodes annotated with go terms obsoleted and replaced by another term

set search_path = panther_upl;
select distinct c.accession, cst.status from paint_annotation pa, 
go_classification_new gcn, go_classification gc, 
node n, classification c, curation_status cs, curation_status_type cst
where pa.node_id = n.node_id
and pa.classification_id = gc.classification_id
and gc.accession = gcn.accession
and gcn.replaced_by_acc is not null
and split_part(n.accession, ':', 1) = c.accession
and c.depth = 5
and c.classification_version_sid = {classification_version_sid}
and n.classification_version_sid = {classification_version_sid}
and c.classification_id = cs.classification_id
and cs.status_type_sid = cst.status_type_sid;

-- insert a new row with “Require paint review” status into curation_status table if you find the records by above query
set search_path = panther_upl;
ALTER TABLE curation_status_old RENAME TO curation_status_new;
truncate table curation_status_new;
insert into curation_status_new select * from curation_status;
insert into curation_status
select nextval('uids'), 7, c.classification_id, 1113, now(), null, null, null
from paint_annotation pa, 
go_classification_new gcn, go_classification gc, 
node n, classification c
where pa.node_id = n.node_id
and pa.classification_id = gc.classification_id
and gc.accession = gcn.accession
and gcn.replaced_by_acc is not null
and split_part(n.accession, ':', 1) = c.accession
and c.depth = 5
and c.classification_version_sid = {classification_version_sid}
and n.classification_version_sid = {classification_version_sid};

-- record the information, insert into comments_new table
set search_path = panther_upl;
ALTER TABLE comments_old RENAME TO comments_new;
truncate table comments_new;
insert into comments_new select * from comments;
update comments_new cm
set remark = cm.remark || '\n' || current_date || ': ' || gc.accession || ' is obsoleted and replaced by ' || gcn.replaced_by_acc || ' so the annotion to ' || n.public_id || ' is updated with new GO term.\n'
from paint_annotation pa, classification c,
go_classification_new gcn, go_classification gc, node n
where c.classification_version_sid = {classification_version_sid}
and n.classification_version_sid = {classification_version_sid}
and c.depth = 5
and c.classification_id = cm.classification_id
and split_part(n.accession,':',1)=c.accession
and pa.node_id = n.node_id
and pa.classification_id = gc.classification_id
and gc.accession = gcn.accession
and gcn.replaced_by_acc is not null
and n.classification_version_sid = {classification_version_sid};

------ ii.	No “replaced_by” tag. Simply obsolete the annotation. Mark the family as “Require paint review”. In the comments table, record the term obsoleted and the PTN IDs

-- find the obsoleted GO terms
set search_path = panther_upl;
select pa.annotation_id, pa.node_id, gcn.accession, gc.accession from paint_annotation_new pa, go_classification_new gcn, go_classification gc
where pa.classification_id = gc.classification_id
and gc.accession = gcn.accession
and gcn.obsolescence_date is not null
and gc.obsolescence_date is null
and gcn.replaced_by_acc is null;

-- insert a new row with “Require paint review” status into curation_status_new table if you find the records by above query
set search_path = panther_upl;
insert into curation_status_new
select nextval('uids'), 7, c.classification_id, 1113, now(), null, null, null
from paint_annotation_new pa, 
go_classification_new gcn, go_classification gc, 
node n, classification c
where pa.node_id = n.node_id
and pa.classification_id = gc.classification_id
and gc.accession = gcn.accession
and gcn.obsolescence_date is not null
and gc.obsolescence_date is null
and gcn.replaced_by_acc is null
and split_part(n.accession, ':', 1) = c.accession
and c.depth = 5
and c.classification_version_sid = {classification_version_sid}
and n.classification_version_sid = {classification_version_sid};

-- record the information in comments table

set search_path = panther_upl;
update comments_new cm
set remark = cm.remark || '\n' || current_date || ': ' || gc.accession || ' is obsoleted and no replaced term, so the annotation to ' || n.public_id || ' is obsoleted.\n'
from paint_annotation_new pa, go_classification_new gcn, go_classification gc, classification c, node n
where pa.node_id = n.node_id
and pa.classification_id = gc.classification_id
and gc.accession = gcn.accession
and gcn.obsolescence_date is not null
and gc.obsolescence_date is null
and gcn.replaced_by_acc is null
and n.classification_version_sid = {classification_version_sid}
and c.classification_version_sid = {classification_version_sid}
and c.depth = 5
and c.classification_id = cm.classification_id
and split_part(n.accession,':',1)=c.accession;

set search_path = panther_upl;
insert into comments_new (comment_id, classification_id, protein_id, remark, created_by, creation_date, obsoleted_by, obsolescence_date, node_id)
select nextval('uids'), c.classification_id, null, current_date || ': ' || gc.accession || ' is obsoleted and no replaced term, so the annotation to ' || n.public_id || ' is obsoleted.\n', 1113, current_date, null, null, null from paint_annotation_new pa, 
go_classification_new gcn, go_classification gc, classification c,
node n
where pa.node_id = n.node_id
and pa.classification_id = gc.classification_id
and gc.accession = gcn.accession
and gcn.obsolescence_date is not null
and gc.obsolescence_date is null
and gcn.replaced_by_acc is null
and n.classification_version_sid = {classification_version_sid}
and c.classification_version_sid = {classification_version_sid}
and c.depth = 5
and split_part(n.accession,':',1)=c.accession
and not exists (select 1 from comments_new cm where c.classification_id = cm.classification_id);