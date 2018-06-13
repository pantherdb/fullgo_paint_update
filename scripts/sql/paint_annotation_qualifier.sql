select aq.annotation_id, q.qualifier from panther_upl.paint_annotation_qualifier aq, panther_upl.qualifier q
where aq.qualifier_id = q.qualifier_id;