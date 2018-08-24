-- need to reload the aggregate data into materialized view go_aggregate, has to drop the view and recreate it, just refresh data won't work because it will still use the old tables
set search_path=panther_upl;
DROP MATERIALIZED VIEW panther_upl.paint_aggregate;

CREATE MATERIALIZED VIEW panther_upl.paint_aggregate AS 
    select pa.annotation_id, n.accession, clf.accession term, et.type, pe.evidence_id, pe.evidence, cc.confidence_code, q.qualifier from paint_evidence pe
    join paint_annotation pa
    on pe.annotation_id = pa.annotation_id
    join confidence_code cc
    on pe.confidence_code_sid = cc.confidence_code_sid
    join node n
    on pa.node_id = n.node_id
    join annotation_type ant
    on pa.annotation_type_id = ant.annotation_type_id and ant.annotation_type = 'GO_PAINT'
    join go_classification clf
    on pa.classification_id = clf.classification_id
    join evidence_type et
    on pe.evidence_type_sid = et.evidence_type_sid
    left join paint_annotation_qualifier pq
    on pa.annotation_id = pq.annotation_id
    left join qualifier q
    on pq.qualifier_id = q.qualifier_id
    where pe.obsolescence_date is null and pa.obsolescence_date is null and n.classification_version_sid = 24  and n.OBSOLESCENCE_DATE is null and clf.OBSOLESCENCE_DATE is null

ALTER TABLE panther_upl.paint_aggregate
  OWNER TO panther_isp;
GRANT ALL ON TABLE panther_upl.paint_aggregate TO panther_isp;
GRANT ALL ON TABLE panther_upl.paint_aggregate TO panther_users;
GRANT ALL ON TABLE panther_upl.paint_aggregate TO panther_paint;
GRANT ALL ON TABLE panther_upl.paint_aggregate TO panther_upl;