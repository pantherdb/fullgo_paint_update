-- For https://github.com/pantherdb/fullgo_paint_update/issues/14 - Ensure HDA go_evidence is created for WBGene00021043 to GO:0005829
set search_path = panther_upl;
select ge.*
  from (
    select distinct gc.classification_id, gw.evidence as ev, et.evidence_type_sid, cc.confidence_code_sid, ga.annotation_id 
    from (
      select geneid, go_acc, confidence_code, split_part(unnest(string_to_array(evidence, '|')), ':', 1) as evidence_type, split_part(unnest(string_to_array(evidence, '|')), ':', 2) as evidence 
      from goanno_wf
	  where geneid = 'CAEEL|WormBase=WBGene00021043|UniProtKB=O44906'
	  and go_acc = 'GO:0005829'
      ) gw, go_classification gc, go_annotation ga, confidence_code cc, gene g, gene_node gn, evidence_type et 
    where gc.accession = gw.go_acc and cc.confidence_code = gw.confidence_code 
    and ga.node_id = gn.node_id and gn.gene_id = g.gene_id and g.classification_version_sid = 24 
    and gw.geneid = g.primary_ext_acc and ga.classification_id = gc.classification_id 
    and upper(gw.evidence_type) = upper(et.type)
  ) ge;

set search_path = panther_upl;
select ge.* from go_annotation ga
join go_evidence ge on ge.annotation_id = ga.annotation_id
join go_classification gc on gc.classification_id = ga.classification_id
join gene_node gn on gn.node_id = ga.node_id
join gene g on g.gene_id = gn.gene_id
-- where ga.annotation_id = 385356306;
where gc.accession = 'GO:0005829'
and g.ext_db_gene_id = 'WBGene00021043'