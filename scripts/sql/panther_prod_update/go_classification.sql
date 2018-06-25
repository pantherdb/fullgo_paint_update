--load data into new tables using below queries

ALTER TABLE go_classification_old RENAME TO go_classification_new;
ALTER TABLE go_classification_relationship_old RENAME TO go_classification_relationship_new;
Truncate table go_classification_new;
Truncate table go_classification_relationship_new;

INSERT INTO go_classification_new(classification_id, classification_version_sid, name,accession, definition,created_by,creation_date,obsolescence_date, term_type_sid,replaced_by_acc) 
SELECT nextval('panther_uids'), 303, ge.name, ge.accession, ge.definition,1,now(), to_date(ge.obsolete_date,'DD:MM:YYYY'), ge.term_type_sid, ge.replaced_by
FROM goobo_extract ge;

INSERT INTO go_classification_new(classification_id, classification_version_sid, name,accession, definition,created_by,creation_date,obsolescence_date,term_type_sid,replaced_by_acc) 
SELECT nextval('panther_uids'), 303, ge.name, ge.alt_id, ge.definition,1,now(), to_date(ge.obsolete_date,'DD:MM:YYYY'), ge.term_type_sid, ge.replaced_by
FROM goobo_extract ge
WHERE ge.alt_id is not null;

insert into go_classification_relationship_new(classification_relationship_id,parent_classification_id,child_classification_id,relationship_type_sid,created_by,creation_date) select NEXTVAL('panther_uids'),c1.classification_id,c2.classification_id,300,1,now() from goobo_parent_child ts join go_classification_new c1 on c1.accession=ts.parent_go join go_classification_new c2 on c2.accession=ts.child_go;