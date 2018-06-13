select e.annotation_id, e.evidence, t.type, c.confidence_code from panther_upl.paint_evidence e, panther_upl.evidence_type t, panther_upl.confidence_code c
where e.evidence_type_sid = t.evidence_type_sid
and e.confidence_code_sid = c.confidence_code_sid
and e.obsolescence_date is null;