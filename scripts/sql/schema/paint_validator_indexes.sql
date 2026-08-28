-- Indexes required by the PAINT validator
-- (edu.usc.ksom.pm.panther.paintServer.tools.FixAnnotUtility, which runs after
-- every data load to re-validate every book with PAINT annotations).
--
-- These are one-time schema setup, NOT part of a data update: none of these
-- tables is rebuilt by the GO/PAINT load, so the indexes persist across loads.
-- They are recorded here so that a database restored from a dump, or moved to a
-- new server, comes back with the same performance instead of silently
-- reverting to a ~24 hour validator run with no error to explain it.
--
-- Safe to re-run: every statement uses IF NOT EXISTS.  Requires PostgreSQL 9.5+.
--
-- Measured on the validator read path, 20-book sample on panthertestdb:
--   before   8,486 ms per book   (~23.7 hours for 10,058 books)
--   after      685 ms per book   (~1.9 hours)
--
-- text_pattern_ops is REQUIRED wherever it appears below and must not be
-- "simplified" away.  The database collation is en_US.UTF-8, and under a non-C
-- collation a plain btree index CANNOT satisfy a LIKE 'prefix%' predicate.
-- Without the operator class the index is created and then silently never used.

set search_path=panther_upl;

-- Prefix lookups on node.accession that do not also filter on version.
CREATE INDEX IF NOT EXISTS idx_node_accession_pat
  ON panther_upl.node (accession text_pattern_ops);

-- The per-book workhorse: equality on classification_version_sid plus a range
-- scan on accession.  The equality column must come first - that is what lets
-- both predicates become index conditions instead of one becoming a post-scan
-- filter that discards ~93% of the rows it fetched.
--
-- Used by DataIO.FULL_GO_ANNOTATIONS_PART_1, PAINT_EXP_ANNOTATION,
-- PANTHER_TREE_STRUCTURE, PANTHER_NODE_ORGANISM and
-- QUERY_ANNOTS_WITH_OBSOLETE_REPLACE_TERMS.
CREATE INDEX IF NOT EXISTS idx_node_ver_accession_pat
  ON panther_upl.node (classification_version_sid, accession text_pattern_ops);

-- DataIO.PANTHER_TREE_STRUCTURE joins node -> node_relationship -> node.
-- node_relationship had only its primary key on node_relationship_id, so every
-- book sequentially scanned all 38,355,302 rows (~2.5 GB of I/O) to find ~185
-- edges: ~4,200 ms per book, and this query runs once per book.
--
-- The index is composite because the query needs both columns from
-- node_relationship (n1.node_id = nr.child_node_id, nr.parent_node_id =
-- n2.node_id), so the join can be satisfied without touching the heap.
CREATE INDEX IF NOT EXISTS idx_node_rel_child_parent
  ON panther_upl.node_relationship (child_node_id, parent_node_id);

-- DataIO.PANTHER_NODE_ORGANISM joins node -> node_organism -> organism.
-- node_organism had no indexes at all, not even a primary key.
CREATE INDEX IF NOT EXISTS idx_node_organism_node_org
  ON panther_upl.node_organism (node_id, organism_id);

-- Without statistics the planner may keep choosing a sequential scan even
-- though the indexes now exist.
ANALYZE panther_upl.node;
ANALYZE panther_upl.node_relationship;
ANALYZE panther_upl.node_organism;
