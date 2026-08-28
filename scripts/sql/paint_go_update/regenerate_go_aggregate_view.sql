-- need to reload the aggregate data into materialized view go_aggregate, has to drop the view and recreate it, just refresh data won't work because it will still use the old tables
set search_path=panther_upl;
DROP MATERIALIZED VIEW IF EXISTS panther_upl.go_aggregate;

CREATE MATERIALIZED VIEW panther_upl.go_aggregate AS 
  SELECT gpa.annotation_id, n.accession, clf.accession AS term, et.type, gpe.evidence_id, gpe.evidence, cc.confidence_code, q.qualifier, gpa.creation_date, gpe.contrib_group
  FROM (
    SELECT go_evidence.annotation_id, go_evidence.confidence_code_sid, go_evidence.evidence_id, go_evidence.evidence, go_evidence.evidence_type_sid, go_evidence.contrib_group
    FROM panther_upl.go_evidence 
    WHERE go_evidence.obsolescence_date IS NULL
  ) gpe 
  JOIN (
    SELECT go_annotation.annotation_id, go_annotation.node_id, go_annotation.annotation_type_id, go_annotation.classification_id, go_annotation.creation_date
    FROM panther_upl.go_annotation 
    WHERE go_annotation.obsolescence_date IS NULL
  ) gpa ON gpe.annotation_id = gpa.annotation_id 
  JOIN panther_upl.confidence_code cc ON gpe.confidence_code_sid::numeric = cc.confidence_code_sid::numeric 
  JOIN panther_upl.node n ON gpa.node_id = n.node_id::numeric 
  JOIN panther_upl.annotation_type ant ON gpa.annotation_type_id = ant.annotation_type_id::numeric AND ant.annotation_type::text = 'FULLGO'::text 
  JOIN panther_upl.go_classification clf ON gpa.classification_id = clf.classification_id 
  JOIN panther_upl.evidence_type et ON gpe.evidence_type_sid::numeric = et.evidence_type_sid::numeric 
  LEFT JOIN panther_upl.go_evidence_qualifier gpq ON gpe.evidence_id = gpq.evidence_id
  LEFT JOIN panther_upl.qualifier q ON gpq.qualifier_id = q.qualifier_id::numeric 
  WHERE n.classification_version_sid::numeric = {classification_version_sid}::numeric AND n.obsolescence_date IS NULL AND clf.obsolescence_date IS NULL WITH DATA;  

-- The PAINT validator (edu.usc.ksom.pm.panther.paintServer.tools.FixAnnotUtility)
-- looks this view up one book at a time, via
--   WHERE accession LIKE 'PTHR12345:%'
-- Without an index that is a sequential scan of the whole view for every book:
-- ~12.5M rows and ~1.5 GB of I/O discarded per book, ~1,800 ms each, repeated
-- for all ~10,000 books.
--
-- text_pattern_ops is REQUIRED and must not be "simplified" away.  The database
-- collation is en_US.UTF-8, and under a non-C collation a plain btree index
-- CANNOT satisfy a LIKE 'prefix%' predicate - the index would be created but
-- silently never used.
CREATE INDEX idx_go_aggregate_accession_pat
  ON panther_upl.go_aggregate (accession text_pattern_ops);

-- A newly created materialized view has no statistics.  Without ANALYZE the
-- planner may keep choosing a sequential scan even though the index exists.
ANALYZE panther_upl.go_aggregate;

-- Owned by panther_upl, the schema this view lives in.  This was previously
-- panther_isp, a role belonging to a different project, which meant nobody on
-- the PAINT side could add an index or otherwise alter the view without a DBA.
ALTER TABLE panther_upl.go_aggregate
  OWNER TO panther_upl;
GRANT ALL ON TABLE panther_upl.go_aggregate TO panther_isp;
GRANT ALL ON TABLE panther_upl.go_aggregate TO panther_users;
GRANT ALL ON TABLE panther_upl.go_aggregate TO panther_paint;
GRANT ALL ON TABLE panther_upl.go_aggregate TO panther_upl;