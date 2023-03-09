-- generate new data and insert into go_evidence_new table, no need to preserve the evidence_id, just erase the old data and repopulate the new data - 19 min.
set search_path=panther_upl;
ALTER TABLE go_evidence_old RENAME TO go_evidence_new;
Truncate table go_evidence_new;
INSERT INTO go_evidence_new(evidence_id, evidence_type_sid, classification_id, evidence, is_editable, confidence_code_sid, annotation_id, contrib_group) 
  select nextval('uids'), ge.evidence_type_sid, ge.classification_id, ge.ev,1, ge.confidence_code_sid, ge.annotation_id, ge.contrib_group
  from (
    select distinct gc.classification_id, gw.evidence as ev, et.evidence_type_sid, cc.confidence_code_sid, ga.annotation_id, gw.contrib_group
    from (
      select geneid, go_acc, confidence_code, split_part(unnest(string_to_array(evidence, '|')), ':', 1) as evidence_type, split_part(unnest(string_to_array(evidence, '|')), ':', 2) as evidence, contrib_group
      from goanno_wf
      ) gw, go_classification_new gc, go_annotation_new ga, confidence_code cc, gene g, gene_node gn, evidence_type et 
    where gc.accession = gw.go_acc and cc.confidence_code = gw.confidence_code 
    and ga.node_id = gn.node_id and gn.gene_id = g.gene_id and g.classification_version_sid = {classification_version_sid}
    and gw.geneid = g.primary_ext_acc and ga.classification_id = gc.classification_id 
    and ga.obsolescence_date is null
    and upper(gw.evidence_type) = upper(et.type)
  ) ge;

REINDEX TABLE panther_upl.go_evidence_new;