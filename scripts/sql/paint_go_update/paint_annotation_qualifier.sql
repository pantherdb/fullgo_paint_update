set search_path = panther_upl;
ALTER TABLE paint_annotation_qualifier_old RENAME TO paint_annotation_qualifier_new;
truncate table paint_annotation_qualifier_new;
insert into paint_annotation_qualifier_new select * from paint_annotation_qualifier;

-- delete all paint_annotation_qualifier records for CONTRIBUTES_TO paint annotations to non-MF terms and COLOCALIZES_WITH to non-CC terms
set search_path = panther_upl;
delete from paint_annotation_qualifier_new pq
using paint_annotation_new pa, go_classification_new gc
where pa.annotation_id = pq.annotation_id
and gc.classification_id = pa.classification_id
and 
((qualifier_id = 64103162 -- CONTRIBUTES_TO
and gc.term_type_sid in (12,13)) -- 12=BP,13=CC
or 
(qualifier_id = 64103161 -- COLOCALIZES_WITH
and gc.term_type_sid in (12,14))); -- 12=BP,14=MF