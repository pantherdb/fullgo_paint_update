-- get_paint_exp_annotations - experimental PAINT annotations for one release.
--
-- Called by the PAINT validator via DataIO.FULL_GO_ANNOTATIONS_PART_3 and
-- FULL_GO_ANNOTATIONS_AGGREGATE, always as:
--
--   SELECT * FROM get_paint_exp_annotations(<version>) WHERE accession LIKE 'PTHR12345:%'
--
-- LANGUAGE sql and STABLE are load-bearing and must not be changed back.
--
-- As LANGUAGE plpgsql this function is an optimization fence: the caller's
-- WHERE accession LIKE '...' cannot be pushed into the body, so PostgreSQL
-- materialises every experimental PAINT annotation for the whole release - all
-- ~10,000 books - and then discards all but one book's rows.  Per book.  It
-- returned zero rows for 19 of 20 sampled books and still cost ~780 ms each.
--
-- A single-SELECT function written in LANGUAGE sql and marked STABLE is a
-- candidate for planner inlining.  Once inlined the body merges into the
-- calling query, the accession predicate lands on node.accession, and
-- idx_node_ver_accession_pat applies.  Measured: 780 ms -> 0.5 ms.
--
-- The default volatility is VOLATILE, which blocks inlining, so STABLE is the
-- part that actually does the work here.  Verify with:
--
--   EXPLAIN (ANALYZE, BUFFERS)
--   SELECT * FROM get_paint_exp_annotations(31) WHERE accession LIKE 'PTHR10000:%';
--
-- A "Function Scan on get_paint_exp_annotations" node in the plan means
-- inlining did NOT happen and the fence is back.  When it works, that node is
-- absent and the underlying joins appear instead.
--
-- The body below is unchanged from the original plpgsql version.

CREATE OR REPLACE FUNCTION panther_upl.get_paint_exp_annotations(p_classification_version_sid integer)
 RETURNS TABLE(annotation_id numeric, accession character varying, term character varying,
               type character varying, evidence_id bigint, evidence character varying,
               confidence_code character varying, qualifier character varying,
               creation_date timestamp without time zone)
 LANGUAGE sql
 STABLE
AS $function$
    SELECT pea.annotation_id,
           n.accession,
           clf.accession AS term,
           et.type,
           pee.evidence_id,
           pee.evidence,
           cc.confidence_code,
           q.qualifier,
           pea.creation_date
      FROM panther_upl.paint_exp_evidence pee
      JOIN panther_upl.paint_exp_annotation pea ON pee.annotation_id::numeric = pea.annotation_id
      JOIN panther_upl.confidence_code cc ON pee.confidence_code_sid = cc.confidence_code_sid
      JOIN panther_upl.node n ON pea.node_id = n.node_id::numeric
      JOIN panther_upl.node_type nt ON n.node_type_id = nt.node_type_id
                                   AND nt.node_type::text = 'LEAF'::text
      JOIN panther_upl.annotation_type ant ON pea.annotation_type_id = ant.annotation_type_id::numeric
                                          AND ant.annotation_type::text = 'GO_PAINT'::text
      JOIN panther_upl.go_classification clf ON pea.classification_id = clf.classification_id
      JOIN panther_upl.evidence_type et ON pee.evidence_type_sid = et.evidence_type_sid
      LEFT JOIN panther_upl.paint_exp_annotation_qualifier peq ON pea.annotation_id = peq.annotation_id
      LEFT JOIN panther_upl.qualifier q ON peq.qualifier_id = q.qualifier_id::numeric
     WHERE pee.obsolescence_date IS NULL
       AND pea.obsolescence_date IS NULL
       AND n.obsolescence_date IS NULL
       AND clf.obsolescence_date IS NULL
       AND n.classification_version_sid = p_classification_version_sid;
$function$;

ALTER FUNCTION panther_upl.get_paint_exp_annotations(integer) OWNER TO panther_upl;
