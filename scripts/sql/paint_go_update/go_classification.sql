-- copy the old data to new table for it to be updated with new data, try to reuse the go_classification_id
set search_path = panther_upl;
ALTER TABLE go_classification_old RENAME TO go_classification_new;
Truncate table go_classification_new;
insert into go_classification_new select * from go_classification;

-- update go entries with the same accession, keep the old go_classification_id
set search_path = panther_upl;
update go_classification_new gcn set name = ge.name, definition = ge.definition, creation_date = now(), obsolescence_date = to_date(ge.obsolete_date, 'YYYY:MM:DD'), term_type_sid = ge.term_type_sid, replaced_by_acc = ge.replaced_by 
from goobo_extract ge  
where gcn.accession = ge.accession;

-- insert new go terms (include alt_id), create new go_classification_id for these new terms (accession not in old table)
set search_path = panther_upl;
INSERT INTO go_classification_new(classification_id, classification_version_sid, name,accession, definition,created_by,creation_date,obsolescence_date,term_type_sid,replaced_by_acc) 
  SELECT nextval('uids'), 303, ge.name, ge.accession, ge.definition,1,now(), to_date(ge.obsolete_date,'YYYY:MM:DD'), ge.term_type_sid, ge.replaced_by 
  FROM goobo_extract ge 
  where ge.accession not in ( select accession from go_classification_new);

-- This only inserts go_classification records for alt_ids if the term is completely new but already obsoleted.
set search_path = panther_upl;
INSERT INTO go_classification_new(classification_id, classification_version_sid, name,accession, definition,created_by,creation_date,obsolescence_date,term_type_sid,replaced_by_acc) 
  SELECT nextval('uids'), 303, ge.name, ge.alt_id, ge.definition,1,now(), to_date(ge.obsolete_date,'YYYY:MM:DD'), ge.term_type_sid, ge.replaced_by 
  FROM goobo_extract ge 
  where ge.alt_id not in ( select accession from go_classification_new);

--obsolete obsoleted go terms in the new table, these go terms having GO accession not in the new data. Needed if obsoletion is done via deletion from obo file.
set search_path = panther_upl;
update go_classification_new set obsoleted_by = 1, obsolescence_date = now() 
where accession not in (select accession from goobo_extract)
and obsolescence_date is null;

-- Update replaced_by for obsoleted terms. Duplicates work for obsoleted terms still existing in obo file but fixes terms that were completely deleted.
set search_path = panther_upl;
update go_classification_new gcn set replaced_by = goo.accession
from goobo_extract goo on goo.alt_id = gcn.accession;

-- generate new go_classification_relationship table, no need to try to keep the old classification_relationship_id, just erase old data and load new data with new id
set search_path = panther_upl;
ALTER TABLE go_classification_relationship_old RENAME TO go_classification_relationship_new;
Truncate table go_classification_relationship_new;
insert into go_classification_relationship_new(classification_relationship_id,parent_classification_id,child_classification_id,relationship_type_sid,created_by,creation_date) 
  select NEXTVAL('uids'),c1.classification_id,c2.classification_id,300,1,now() 
  from goobo_parent_child ts 
  join go_classification_new c1 on c1.accession=ts.parent_go 
  join go_classification_new c2 on c2.accession=ts.child_go;