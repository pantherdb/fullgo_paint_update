select gc.accession, q.qualifier, g.primary_ext_acc, to_char(pea.creation_date,'YYYY-MM-DD') as creation_date, cc.confidence_code, concat(et.type, ':', pee.evidence) as reference
from panther_upl.paint_exp_annotation pea 
join panther_upl.paint_exp_evidence pee on pee.annotation_id = pea.annotation_id 
left join panther_upl.paint_exp_annotation_qualifier peaq on peaq.annotation_id = pea.annotation_id
left join panther_upl.qualifier q on q.qualifier_id = peaq.qualifier_id 
join panther_upl.go_classification gc on gc.classification_id = pea.classification_id 
join panther_upl.gene_node gn on gn.node_id = pea.node_id 
join panther_upl.gene g on g.gene_id = gn.gene_id 
join panther_upl.confidence_code cc on cc.confidence_code_sid = pee.confidence_code_sid 
join panther_upl.evidence_type et on et.evidence_type_sid = pee.evidence_type_sid 
where pea.obsolescence_date is null;