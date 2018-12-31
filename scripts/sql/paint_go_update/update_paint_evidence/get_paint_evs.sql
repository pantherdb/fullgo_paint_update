select pen.evidence, paq.qualifier_id, pen.evidence_id from panther_upl.paint_evidence_new pen
left join panther_upl.paint_annotation_qualifier paq on paq.annotation_id = pen.annotation_id
where pen.obsolescence_date is null;