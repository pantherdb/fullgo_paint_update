-- generate new go_classification_relationship table, no need to try to keep the old classification_relationship_id, just erase old data and load new data with new id
set search_path = panther_upl;
ALTER TABLE go_classification_relationship_old RENAME TO go_classification_relationship_new;
Truncate table go_classification_relationship_new;
insert into go_classification_relationship_new(classification_relationship_id,parent_classification_id,child_classification_id,relationship_type_sid,created_by,creation_date) 
  select NEXTVAL('uids'),c1.classification_id,c2.classification_id,300,1,now() 
  from goobo_parent_child ts 
  join go_classification_new c1 on c1.accession=ts.parent_go 
  join go_classification_new c2 on c2.accession=ts.child_go;