-- Restore obsolescence_dates to paint_evidence records that were previously obsoleted_by curators but erroneously unobsoleted by monthly update
-- Two time periods to restore:
--   1. Pre-Aug2018 panther_upl.paint_evidence_obs
--   2. Aug2018-Sep2018 panther_upl.paint_evidence_obs_hm (Includes erased fixes Huaiyu made for https://github.com/pantherdb/fullgo_paint_update/issues/8)

set search_path = panther_upl;

-- Select current state for time period #1
select n.public_id, gc.accession, u.name as obsoleted_by, obs.obsolescence_date from panther_upl.paint_evidence pe
join panther_upl.paint_evidence_obs obs on obs.annotation_id = pe.annotation_id
and obs.confidence_code_sid = pe.confidence_code_sid
and obs.evidence = pe.evidence
and obs.evidence_type_sid = pe.evidence_type_sid
join panther_upl.paint_annotation pa on pa.annotation_id = obs.annotation_id
join panther_upl.node n on n.node_id = pa.node_id
join panther_upl.go_classification gc on gc.classification_id = pa.classification_id
join panther_upl.users u on u.user_id = cast(obs.obsoleted_by as int)
where pe.obsolescence_date is null and obs.obsolescence_date is not null
and obs.obsoleted_by != '1'
group by n.public_id, gc.accession, u.name, obs.obsolescence_date
order by obs.obsolescence_date;

-- Fix for time period #1 - 19 rows?
update panther_upl.paint_evidence pe
set obsolescence_date = obs.obsolescence_date, obsoleted_by = obs.obsoleted_by
from panther_upl.paint_evidence_obs obs
join panther_upl.paint_annotation pa on pa.annotation_id = obs.annotation_id
where obs.annotation_id = pe.annotation_id
and obs.confidence_code_sid = pe.confidence_code_sid
and obs.evidence = pe.evidence
and obs.evidence_type_sid = pe.evidence_type_sid
and pe.obsolescence_date is null and obs.obsolescence_date is not null
and obs.obsoleted_by != '1';

-- Check current results after first query
-- Select current state for time period #2
select n.public_id, gc.accession, u.name as obsoleted_by, obs.obsolescence_date from panther_upl.paint_evidence pe
join panther_upl.paint_evidence_obs_hm obs on obs.annotation_id = pe.annotation_id
and obs.confidence_code_sid = pe.confidence_code_sid
and obs.evidence = pe.evidence
and obs.evidence_type_sid = pe.evidence_type_sid
join panther_upl.paint_annotation pa on pa.annotation_id = obs.annotation_id
join panther_upl.node n on n.node_id = pa.node_id
join panther_upl.go_classification gc on gc.classification_id = pa.classification_id
join panther_upl.users u on u.user_id = cast(obs.obsoleted_by as int)
where pe.obsolescence_date is null and obs.obsolescence_date is not null
and obs.obsoleted_by != '1'
group by n.public_id, gc.accession, u.name, obs.obsolescence_date
order by obs.obsolescence_date;

-- Fix for time period #2 - 307 rows?
update panther_upl.paint_evidence pe
set obsolescence_date = obs.obsolescence_date, obsoleted_by = obs.obsoleted_by
from panther_upl.paint_evidence_obs_hm obs
join panther_upl.paint_annotation pa on pa.annotation_id = obs.annotation_id
where obs.annotation_id = pe.annotation_id
and obs.confidence_code_sid = pe.confidence_code_sid
and obs.evidence = pe.evidence
and obs.evidence_type_sid = pe.evidence_type_sid
and pe.obsolescence_date is null and obs.obsolescence_date is not null
and obs.obsoleted_by != '1';