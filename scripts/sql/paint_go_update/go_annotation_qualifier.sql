-- insert new data into empty go_annotation_qualifier_new table, erase old data and regenerate new data with new row id number
set search_path=panther_upl;
ALTER TABLE go_annotation_qualifier_old RENAME TO go_annotation_qualifier_new;
truncate table go_annotation_qualifier_new;
INSERT INTO go_annotation_qualifier_new(annotation_qualifier_id, annotation_id, qualifier_id) 
  select nextval('uids'), ga.annotation_id, q.qualifier_id 
  from go_annotation_new ga, go_classification_new gc, goanno_wf gw, gene g, gene_node gn, qualifier q 
  where ga.node_id = gn.node_id and gn.gene_id = g.gene_id and ga.obsolescence_date is null 
  and g.classification_version_sid = {classification_version_sid} and gw.geneid = g.primary_ext_acc 
  and ga.classification_id = gc.classification_id and gc.accession = gw.go_acc 
  and q.qualifier = upper(gw.qualifier);