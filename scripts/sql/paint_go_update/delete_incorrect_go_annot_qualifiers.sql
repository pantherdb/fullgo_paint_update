-- delete all go_annotation_qualifier records for CONTRIBUTES_TO go annotations to non-MF terms and COLOCALIZES_WITH to non-CC terms
set search_path = panther_upl;
delete from go_annotation_qualifier gq
using go_annotation ga, go_classification gc
where ga.annotation_id = gq.annotation_id
and gc.classification_id = ga.classification_id
and 
((qualifier_id = 64103162 -- CONTRIBUTES_TO
and gc.term_type_sid in (12,13)) -- 12=BP,13=CC
or 
(qualifier_id = 64103161 -- COLOCALIZES_WITH
and gc.term_type_sid in (12,14))); -- 12=BP,14=MF