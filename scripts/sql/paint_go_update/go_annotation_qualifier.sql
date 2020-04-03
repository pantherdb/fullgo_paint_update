-- insert new data into empty go_annotation_qualifier_new table, erase old data and regenerate new data with new row id number
set search_path=panther_upl;
ALTER TABLE go_annotation_qualifier_old RENAME TO go_annotation_qualifier_new;
truncate table go_annotation_qualifier_new;
INSERT INTO go_annotation_qualifier_new(annotation_qualifier_id, annotation_id, qualifier_id) 
  select nextval('uids'), ga.annotation_id, q.qualifier_id 
  from go_annotation_new ga, go_classification_new gc, goanno_wf gw, gene g, gene_node gn, qualifier q 
  where ga.node_id = gn.node_id and gn.gene_id = g.gene_id and ga.obsolescence_date is null 
  and g.classification_version_sid = {classification_version_sid} and gw.geneid = g.primary_ext_acc 
  and ga.classification_id = gc.classification_id and gc.accession = gw.go_acc 
  and q.qualifier = upper(gw.qualifier);

-- Keeping this but switching to using go_evidence_qualifier table below
-- -- Fill annotation_qualifier_id column on go_evidence
-- -- Use goanno_wf to associate to go_evidence
-- set search_path = panther_upl;
-- update go_evidence_new ge_u
-- set annotation_qualifier_id = gaq.annotation_qualifier_id
-- from go_evidence_new ge
-- join go_annotation_new ga on ga.annotation_id = ge.annotation_id
-- join gene_node gn on gn.node_id = ga.node_id
-- join gene g on g.gene_id = gn.gene_id
-- join go_classification_new gc on gc.classification_id = ga.classification_id
-- join confidence_code cc on cc.confidence_code_sid = ge.confidence_code_sid
-- join evidence_type et on et.evidence_type_sid = ge.evidence_type_sid
-- join go_annotation_qualifier_new gaq on gaq.annotation_id = ga.annotation_id
-- join qualifier q on q.qualifier_id = gaq.qualifier_id
-- join (select geneid, go_acc, confidence_code, split_part(unnest(string_to_array(evidence, '|')), ':', 1) as evidence_type, split_part(unnest(string_to_array(evidence, '|')), ':', 2) as evidence, qualifier 
--       from goanno_wf
--       where qualifier is not null) gw
--       on gw.geneid = g.primary_ext_acc
--       and gw.go_acc = gc.accession
--       and gw.confidence_code = cc.confidence_code
--       and gw.evidence_type = et.type
--       and gw.evidence = ge.evidence
--       and upper(gw.qualifier) = q.qualifier
-- where g.classification_version_sid = {classification_version_sid}
-- and ge_u.evidence_id = ge.evidence_id;

set search_path=panther_upl;
DROP MATERIALIZED VIEW panther_upl.goanno_w_qualifier;

CREATE MATERIALIZED VIEW panther_upl.goanno_w_qualifier AS 
  select geneid, go_acc, confidence_code, split_part(unnest(string_to_array(evidence, '|')), ':', 1) as evidence_type, split_part(unnest(string_to_array(evidence, '|')), ':', 2) as evidence, upper(unnest(string_to_array(qualifier, '|'))) as qualifier 
  from panther_upl.goanno_wf
  where qualifier is not null;

ALTER TABLE panther_upl.goanno_w_qualifier
  OWNER TO panther_isp;
GRANT ALL ON TABLE panther_upl.goanno_w_qualifier TO panther_isp;
GRANT ALL ON TABLE panther_upl.goanno_w_qualifier TO panther_users;
GRANT ALL ON TABLE panther_upl.goanno_w_qualifier TO panther_paint;
GRANT ALL ON TABLE panther_upl.goanno_w_qualifier TO panther_upl;

-- insert new data into empty go_evidence_qualifier_new table, erase old data and regenerate new data with new row id number
-- This splits on qualifier delimiters unlike go_annotation_qualifier_new above; need to fix later
set search_path=panther_upl;
ALTER TABLE go_evidence_qualifier_old RENAME TO go_evidence_qualifier_new;
truncate table go_evidence_qualifier_new;

INSERT INTO go_evidence_qualifier_new(evidence_qualifier_id, evidence_id, qualifier_id) 
  select nextval('uids'), x.evidence_id, x.qualifier_id from
    (select distinct ge.evidence_id, q.qualifier_id 
    from goanno_w_qualifier gw
    join gene g on g.primary_ext_acc = gw.geneid
    join gene_node gn on gn.gene_id = g.gene_id
    join go_classification_new gc on gc.accession = gw.go_acc
    join go_annotation_new ga on ga.node_id = gn.node_id and ga.classification_id = gc.classification_id
    join evidence_type et on et.type = gw.evidence_type
    join go_evidence_new ge on ge.annotation_id = ga.annotation_id and ge.evidence_type_sid = et.evidence_type_sid and ge.evidence = gw.evidence
    join qualifier q on gw.qualifier = q.qualifier
    where g.classification_version_sid = {classification_version_sid}) x;