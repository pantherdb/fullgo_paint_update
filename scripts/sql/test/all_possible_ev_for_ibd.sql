select distinct ga.annotation_id go_annotation_id, pa.annotation_id paint_annotation_id, gcp.accession, gcg.accession, g.primary_ext_acc
from
(select parent_node_acc, unnest(string_to_array(child_leaf_node_acc, ',')) as leaf from node_all_leaves_v14_1) pl
join node n on n.accession = pl.parent_node_acc
join node n1 on n1.accession = pl.leaf
join paint_annotation_new pa on pa.node_id = n.node_id
join go_classification_descendants dd on dd.parent_classification_id = pa.classification_id
--join go_annotation_new ga on ga.node_id = n1.node_id and ga.classification_id = pa.classification_id -- all GO annots to any leaf node with same term
join go_annotation_new ga on ga.node_id = n1.node_id and (ga.classification_id = pa.classification_id or ga.classification_id::varchar(255) = any(string_to_array(dd.desc_classification_ids, ','))) -- all GO annots to any leaf node with same term
join paint_evidence_new pe on pe.annotation_id = pa.annotation_id -- and cast(pe.evidence as int) = ga.annotation_id -- all paint_ev to this paint_annot w/ GO annot already hooked up
join go_evidence_new ge on ge.annotation_id = ga.annotation_id
join confidence_code cc on cc.confidence_code_sid = ge.confidence_code_sid
--left join go_annotation_qualifier_new gaq on gaq.annotation_id = ga.annotation_id
left join go_evidence_qualifier_new geq on geq.evidence_id = ge.evidence_id
left join paint_annotation_qualifier paq on paq.annotation_id = pa.annotation_id
join go_classification_new gcp on gcp.classification_id = pa.classification_id
join go_classification_new gcg on gcg.classification_id = ga.classification_id
join gene_node gn on gn.node_id = n1.node_id
join gene g on g.gene_id = gn.gene_id
where pe.evidence_type_sid = 46  -- still need paint_evidence to isolate IBDs - we can allow obsolete paint_evidences too
and n.classification_version_sid = 26
and n1.classification_version_sid = 26
and ga.annotation_id != pe.annotation_id
and ga.obsolescence_date is null
and (pa.obsoleted_by = 1 or pa.obsoleted_by is null) -- Only touch annotations non-obsolete or obsoleted by system
and (geq.qualifier_id = paq.qualifier_id or (geq.evidence_qualifier_id is null and paq.annotation_qualifier_id is null))
and cc.confidence_code in ('EXP', 'IDA', 'IPI', 'IMP', 'IGI', 'IEP', 'HTP', 'HDA', 'HMP', 'HGI', 'HEP')
--and n.public_id = 'PTN000605377' -- IBD node from https://github.com/pantherdb/fullgo_paint_update/issues/36 - add check if exists in paint_evidence

--and n.public_id = 'PTN000045135'
--and gcp.accession = 'GO:0030136'

--and n.public_id = 'PTN000894784' -- GO:0000790	GO:0005719	HUMAN|HGNC=6204|UniProtKB=P05412 - GOOD EXAMPLE
and n.public_id = 'PTN001258412' -- GO:0015672