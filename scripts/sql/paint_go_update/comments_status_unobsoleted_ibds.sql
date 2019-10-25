-- DATE-DEPENDENT; MUST BE UPDATED EACH RUN TO DATE paint_annotation TABLE WAS UPDATED

-- find the panther families that have IBD annotations loses all the evidental leaf experimental annotations
-- set search_path=panther_upl;
-- select distinct c.accession from paint_annotation_new pa, paint_evidence_new pe, node n, classification c
-- where pa.annotation_id not in (
--   select pe.annotation_id
--   from paint_evidence_new pe, paint_annotation_new pa
--   where pe.annotation_id = pa.annotation_id
--   and pe.evidence_type_sid = 46
--   and pe.obsoleted_by is null
-- )
-- and pa.annotation_id = pe.annotation_id
-- and pe.evidence_type_sid = 46
-- and pa.obsolescence_date > '2018-09-26'
-- and pa.obsoleted_by = 1
-- and pa.node_id = n.node_id
-- and n.classification_version_sid = {classification_version_sid}
-- and split_part(n.accession, ':', 1) = c.accession
-- and c.depth = 5
-- and c.classification_version_sid = {classification_version_sid};


set search_path = panther_upl;
insert into curation_status_new
select nextval('uids'), 7, x.classification_id, 1113, now(), null, null, null
from (
select distinct c.classification_id
from paint_annotation_new pan
join paint_annotation pa on pa.annotation_id = pan.annotation_id
join node n on n.node_id = pan.node_id
join classification c on c.accession = split_part(n.accession, ':', 1) and c.classification_version_sid = {classification_version_sid}
join go_classification_new gc on gc.classification_id = pan.classification_id
where pan.obsolescence_date is null
and pa.obsolescence_date is not null
and not exists (
	-- check if valid evidence for annotation_id didn't previously exist in evidence table
	select 1 from paint_evidence pe
	where pe.annotation_id = pan.annotation_id
	and pe.obsolescence_date is null
)
) x;

set search_path = panther_upl;
update comments_new cm
set remark = cm.remark || '.\n' || x.remark_n
from
(
select c.classification_id, string_agg(current_date || ': PAINT annotation to ' || n.public_id || ' with ' || gc.accession || ' was unobsoleted because it now has valid experimental evidence.\n', '') as remark_n
from paint_annotation_new pan
join paint_annotation pa on pa.annotation_id = pan.annotation_id
join node n on n.node_id = pan.node_id
join classification c on c.accession = split_part(n.accession, ':', 1) and c.classification_version_sid = {classification_version_sid}
join go_classification_new gc on gc.classification_id = pan.classification_id
where pan.obsolescence_date is null
and pa.obsolescence_date is not null
and not exists (
	-- check if valid evidence for annotation_id didn't previously exist in evidence table
	select 1 from paint_evidence pe
	where pe.annotation_id = pan.annotation_id
	and pe.obsolescence_date is null
)
group by c.classification_id
) x
where cm.classification_id = x.classification_id;

set search_path = panther_upl;
insert into comments_new (comment_id, classification_id, protein_id, remark, created_by, creation_date, obsoleted_by, obsolescence_date, node_id)
select nextval('uids'), x.classification_id, null, x.remark_n, 1113, current_date, null, null, null
from
(
select c.classification_id, string_agg(current_date || ': PAINT annotation to ' || n.public_id || ' with ' || gc.accession || ' was unobsoleted because it now has valid experimental evidence.\n', '') as remark_n
from paint_annotation_new pan
join paint_annotation pa on pa.annotation_id = pan.annotation_id
join node n on n.node_id = pan.node_id
join classification c on c.accession = split_part(n.accession, ':', 1) and c.classification_version_sid = {classification_version_sid}
join go_classification_new gc on gc.classification_id = pan.classification_id
where pan.obsolescence_date is null
and pa.obsolescence_date is not null
and not exists (
	-- check if valid evidence for annotation_id didn't previously exist in evidence table
	select 1 from paint_evidence pe
	where pe.annotation_id = pan.annotation_id
	and pe.obsolescence_date is null
)
group by c.classification_id
) x
where not exists (select 1 from comments_new cm where x.classification_id = cm.classification_id);
