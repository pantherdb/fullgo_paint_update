select pa.annotation_id, n.accession, n.public_id, c.accession, c.name, t.term_name, pa.creation_date
from panther_upl.paint_annotation pa, panther_upl.node n, panther_upl.go_classification c, panther_upl.classification_term_type t
where pa.node_id = n.node_id
and n.obsolescence_date is null
and pa.classification_id = c.classification_id
and c.obsolescence_date is null
and pa.obsolescence_date is null
and c.term_type_sid = t.term_type_sid;