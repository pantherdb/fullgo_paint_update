--copy data to new paint annotation table to be updated, old table serve as a backup, try to keep the annotation_id that didn't change annotation
set search_path = panther_upl;
--due to the _fix table switcheroos the _new tables will always be hanging around
--ALTER TABLE paint_annotation_old RENAME TO paint_annotation_new;
Truncate table paint_annotation_new;
insert into paint_annotation_new select * from paint_annotation;

--obsolete the paint annotations with go classification terms that are obsoleted and no replaced term in go_classification_new table.
set search_path = panther_upl;
update paint_annotation_new pan 
set obsolescence_date = gcn.obsolescence_date, obsoleted_by = 1 
from go_classification_new gcn 
where pan.classification_id = gcn.classification_id 
and gcn.obsolescence_date is not null 
and gcn.replaced_by_acc is null;

--replace the go term classification_id in paint annotations that are obsoleted and replaced with another go term with the classification_id of the replacing go term
set search_path = panther_upl;
update paint_annotation_new pan 
set classification_id = gcn2.classification_id 
from go_classification_new gcn1, go_classification_new gcn2 
where pan.classification_id = gcn1.classification_id 
and gcn1.replaced_by_acc is not null 
and gcn2.accession = gcn1.replaced_by_acc;

