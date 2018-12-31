select gan.annotation_id, gaq.qualifier_id from panther_upl.go_annotation_new gan 
join panther_upl.go_evidence_new gen on gen.annotation_id = gan.annotation_id
left join panther_upl.go_annotation_qualifier_new gaq on gaq.annotation_id = gan.annotation_id
where gan.obsolescence_date is null
and gen.confidence_code_sid in (1,2,4,5,11,13,18,19,20,21,22);