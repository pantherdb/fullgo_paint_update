-- copy go_annotation data to a new table to be updated with new data, , old table serve as a backup, try to keep old annotation_id as much as possible if the node and go_classification are the same with the old data
set search_path = panther_upl;
ALTER TABLE go_annotation_old RENAME TO go_annotation_new;
Truncate table go_annotation_new;
insert into go_annotation_new select * from go_annotation;

-- for the new fullgo annotation data (node and go_classification combination) (from goanno_wf foreign table loaded with new fullgo data in production database) that are not in the go_annotation_new table, insert them into the table as new rows with new annotation_id - 26 min
set search_path = panther_upl;
insert into go_annotation_new(annotation_id, node_id, classification_id, annotation_type_id, created_by, creation_date)
  select nextval('uids'), x.node_id, x.classification_id, 2, 1, now() 
  from (
    select distinct gn.node_id, gc.classification_id 
    from gene_node gn 
    join gene g on g.gene_id = gn.gene_id and g.classification_version_sid = {classification_version_sid} 
    join goanno_wf gw on g.primary_ext_acc = gw.geneid 
    join go_classification_new gc on gc.accession = gw.go_acc 
    where not exists  (select 1 from go_annotation_new gan where gn.node_id = gan.node_id and gc.classification_id = gan.classification_id and gan.obsolescence_date is null)
  ) x; 

-- for the previous fullgo annotation no longer in the new data in the goanno_wf table, mark them as obsoleted - 27 min
set search_path = panther_upl;
update go_annotation_new gan 
set obsoleted_by = 1, obsolescence_date = now() 
where not exists (
  select 1 from gene_node gn, gene g, goanno_wf gw, go_classification_new gc 
  where g.gene_id = gn.gene_id 
  and g.classification_version_sid = {classification_version_sid} 
  and g.primary_ext_acc = gw.geneid 
  and gc.accession = gw.go_acc 
  and gn.node_id = gan.node_id 
  and gc.classification_id = gan.classification_id
  )
and gan.obsolescence_date is null;

--for go_annotation entry with obsoleted go term, but no replaced go term, obsolete the go_annotation entry
set search_path = panther_upl;
update go_annotation_new gan 
set obsoleted_by = 1, obsolescence_date = now() 
from go_classification_new gcn 
where gan.classification_id = gcn.classification_id 
and gcn.obsolescence_date is not null 
and gcn.replaced_by_acc is null
and gan.obsolescence_date is null;

--for go_annotation entry with go term replaced by another go term, change the classification_id to that of the new go term
set search_path = panther_upl;
update go_annotation_new gan set classification_id = gcn1.classification_id 
from go_classification_new gcn, go_classification_new gcn1 
where gan.classification_id = gcn.classification_id 
and gcn.replaced_by_acc is not null 
and gcn.replaced_by_acc = gcn1.accession;