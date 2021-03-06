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

--update curation_status_new table for the families with paint_annotation lost all evidence leaf annotations to 'Require paint review'
set search_path = panther_upl;
insert into curation_status_new
select nextval('uids'), 7, x.classification_id, 1113, now(), null, null, null
from (
select distinct c.classification_id
from paint_annotation_new pa, paint_evidence_new pe, node n, classification c
where pa.annotation_id not in (
select pe.annotation_id
from paint_evidence_new pe, paint_annotation_new pa
where pe.annotation_id = pa.annotation_id
and pe.evidence_type_sid = 46
and pe.obsoleted_by is null)
and pa.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 46
and pa.obsolescence_date > '2019-10-24' -- need to update the date every time
and pa.obsoleted_by = 1
and pa.node_id = n.node_id
and n.classification_version_sid = {classification_version_sid}
and split_part(n.accession, ':', 1) = c.accession
and c.depth = 5
and c.classification_version_sid = {classification_version_sid}
) x;

-- record the information in comments table
set search_path = panther_upl;
update comments_new cm
set remark = cm.remark || '\n' || current_date || ': ' || '.\n'
from
(select distinct c.classification_id, gc.accession go_acc, n.public_id, n1.public_id paint_evidence_leaf_node, gc1.accession go_annotation_go_term
from paint_annotation_new pa, paint_evidence_new pe, node n, classification c, go_classification_new gc, go_annotation_new ga, node n1, go_classification_new gc1
where pa.annotation_id not in (
select pe.annotation_id
from paint_evidence_new pe, paint_annotation_new pa
where pe.annotation_id = pa.annotation_id
and pe.evidence_type_sid = 46
and pe.obsoleted_by is null)
and pa.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 46
and pa.obsolescence_date > '2019-10-24' -- need to update the date every time
and pa.obsoleted_by = 1
and pa.node_id = n.node_id
and n.classification_version_sid = {classification_version_sid}
and split_part(n.accession, ':', 1) = c.accession
and c.depth = 5
and c.classification_version_sid = {classification_version_sid}
and pa.classification_id = gc.classification_id
and cast(pe.evidence as integer) = ga.annotation_id
and ga.node_id = n1.node_id
and ga.classification_id = gc1.classification_id
and n1.classification_version_sid = {classification_version_sid}) y
where cm.classification_id = y.classification_id;

set search_path = panther_upl;
update comments_new cm
set remark = cm.remark || '.\n' || x.remark_n
from
(
select k.classification_id, string_agg(current_date || ': PAINT annotation to ' || k.ibd_public_id || ' with ' || k.ibd_accession || ' lost all leaf node experimental evidence, including experimental annotation to leaf node ' || k.leaf_public_id || ' with ' || k.leaf_accession || ' so it is obsoleted.\n', '') as remark_n
from (select distinct c.classification_id, n.public_id ibd_public_id, gc.accession ibd_accession, n1.public_id leaf_public_id, gc1.accession leaf_accession
from paint_annotation_new pa, paint_evidence_new pe, node n, classification c, go_classification_new gc, go_annotation_new ga, node n1, go_classification_new gc1
where pa.annotation_id not in (
select pe.annotation_id
from paint_evidence_new pe, paint_annotation_new pa
where pe.annotation_id = pa.annotation_id
and pe.evidence_type_sid = 46
and pe.obsoleted_by is null)
and pa.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 46
and pa.obsolescence_date > '2019-10-24' -- need to update the date every time
and pa.obsoleted_by = 1
and pa.node_id = n.node_id
and n.classification_version_sid = {classification_version_sid}
and split_part(n.accession, ':', 1) = c.accession
and c.depth = 5
and c.classification_version_sid = {classification_version_sid}
and pa.classification_id = gc.classification_id
and cast(pe.evidence as integer) = ga.annotation_id
and ga.node_id = n1.node_id
and ga.classification_id = gc1.classification_id
and n1.classification_version_sid = {classification_version_sid}
) k
group by k.classification_id
) x
where cm.classification_id = x.classification_id;

set search_path = panther_upl;
insert into comments_new (comment_id, classification_id, protein_id, remark, created_by, creation_date, obsoleted_by, obsolescence_date, node_id)
select nextval('uids'), x.classification_id, null, x.remark_n, 1113, current_date, null, null, null
from
(
select k.classification_id, string_agg(current_date || ': PAINT annotation to ' || k.ibd_public_id || ' with ' || k.ibd_accession || ' lost all leaf node experimental evidence, including experimental annotation to leaf node ' || k.leaf_public_id || ' with ' || k.leaf_accession || ' so it is obsoleted.\n', '') as remark_n
from (select distinct c.classification_id, n.public_id ibd_public_id, gc.accession ibd_accession, n1.public_id leaf_public_id, gc1.accession leaf_accession
from paint_annotation_new pa, paint_evidence_new pe, node n, classification c, go_classification_new gc, go_annotation_new ga, node n1, go_classification_new gc1
where pa.annotation_id not in (
select pe.annotation_id
from paint_evidence_new pe, paint_annotation_new pa
where pe.annotation_id = pa.annotation_id
and pe.evidence_type_sid = 46
and pe.obsoleted_by is null)
and pa.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 46
and pa.obsolescence_date > '2019-10-24' -- need to update the date every time
and pa.obsoleted_by = 1
and pa.node_id = n.node_id
and n.classification_version_sid = {classification_version_sid}
and split_part(n.accession, ':', 1) = c.accession
and c.depth = 5
and c.classification_version_sid = {classification_version_sid}
and pa.classification_id = gc.classification_id
and cast(pe.evidence as integer) = ga.annotation_id
and ga.node_id = n1.node_id
and ga.classification_id = gc1.classification_id
and n1.classification_version_sid = {classification_version_sid}
) k
group by k.classification_id
) x
where not exists (select 1 from comments_new cm where x.classification_id = cm.classification_id);
