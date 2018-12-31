-- 1.	The GO ID is no longer the primary ID in the obo file.
---- b.	The GO ID is not obsoleted
------ i.	It is a secondary ID (or alt_id) to a different term. This means the two terms are merged. Replace the GO term with the merged term. Mark the family as “Require paint review”. In the comments table, record the old and new GO ids and terms, and indicate that this is a merge. This is to differentiate it from obsoletion. (Example: GO:0003723 and GO:0044822). 

-- find the go terms that have alt_id
set search_path = panther_upl;
select gcn.accession, string_agg(gen.alt_id, ',') as alt_acc from go_classification_new gcn, goobo_extract gen
where gcn.accession = gen.accession
and gen.alt_id is not null
group by 1;

-- update go_classification_new table with alt_id
set search_path = panther_upl;
update go_classification_new gcn
set alt_acc = x.alt_acc
from
(select gen.accession, string_agg(gen.alt_id, ',') as alt_acc from goobo_extract gen
where gen.alt_id is not null
group by 1) x
where gcn.accession = x.accession;

--update the curation_status table for the families with paint_annotation of alt go terms, insert a status of 'require paint review'
set search_path = panther_upl;
insert into curation_status_new
select nextval('uids'), 7, y.classification_id, 1113, now(), null, null, null
from 
(select distinct c.classification_id
from paint_annotation_new pa,
(select accession, BTRIM(unnest(string_to_array(alt_acc, ','))) as alt_acc from go_classification_new
where alt_acc is not null) x, go_classification_new gc, go_classification_new gc1, node n, classification c
where pa.classification_id = gc.classification_id
and gc.accession = x.alt_acc
and x.accession = gc1.accession
and pa.node_id = n.node_id
and n.classification_version_sid = {classification_version_sid}
and split_part(n.accession, ':', 1) = c.accession
and c.depth = 5
and c.classification_version_sid = {classification_version_sid}) y;

--record the information in comments table
set search_path = panther_upl;
update comments_new cm
set remark = cm.remark || '\n' || current_date || ': ' || y.alt_acc || ' is alternative accession to ' || y.go_acc || ' , this is a merge, so annotation to ' || y.public_id || ' is updated with primary GO accession ' || y.go_acc || '.\n'
from
(select distinct c.classification_id, c.accession fam, gc1.accession go_acc, gc.accession alt_acc, n.public_id
from paint_annotation_new pa,
(select accession, BTRIM(unnest(string_to_array(alt_acc, ','))) as alt_acc from go_classification_new
where alt_acc is not null) x, go_classification_new gc, go_classification_new gc1, node n, classification c
where pa.classification_id = gc.classification_id
and gc.accession = x.alt_acc
and x.accession = gc1.accession
and pa.node_id = n.node_id
and n.classification_version_sid = {classification_version_sid}
and split_part(n.accession, ':', 1) = c.accession
and c.depth = 5
and c.classification_version_sid = {classification_version_sid}) y
where cm.classification_id = y.classification_id;

insert into comments_new (comment_id, classification_id, protein_id, remark, created_by, creation_date, obsoleted_by, obsolescence_date, node_id)
select nextval('uids'), y.classification_id, null, current_date || ': ' || y.alt_acc || ' is alternative accession to ' || y.go_acc || ' , this is a merge, so annotation to ' || y.public_id || ' is updated with primary GO accession ' || y.go_acc || '.\n', 1113, current_date, null, null, null
from
(select distinct c.classification_id, c.accession fam, gc1.accession go_acc, gc.accession alt_acc, n.public_id
from paint_annotation_new pa,
(select accession, BTRIM(unnest(string_to_array(alt_acc, ','))) as alt_acc from go_classification_new
where alt_acc is not null) x, go_classification_new gc, go_classification_new gc1, node n, classification c
where pa.classification_id = gc.classification_id
and gc.accession = x.alt_acc
and x.accession = gc1.accession
and pa.node_id = n.node_id
and n.classification_version_sid = {classification_version_sid}
and split_part(n.accession, ':', 1) = c.accession
and c.depth = 5
and c.classification_version_sid = {classification_version_sid}) y
where not exists (select 1 from comments_new cm where y.classification_id = cm.classification_id);

--replace the go term classification_id in paint_annotation_new table that are alt_id of another primary go term with the classification_id of the primary go term
set search_path = panther_upl;
update paint_annotation_new pan
set classification_id = gc1.classification_id
from (select accession, BTRIM(unnest(string_to_array(alt_acc, ','))) as alt_acc from go_classification
where alt_acc is not null) x, go_classification_new gc, go_classification_new gc1, node n
where pan.classification_id = gc.classification_id
and gc.accession = x.alt_acc
and x.accession = gc1.accession
and pan.node_id = n.node_id
and n.classification_version_sid = {classification_version_sid};

------ ii.	It is not a secondary ID. This means the GO id simply disappears, which should never happen. Need to contact GO.

-- find the paint_annotation table contained go terms that are not in go_classification table (either primary accession or alternative accession)
set search_path = panther_upl;
select * from paint_annotation_new pa, go_classification_new gc
where pa.classification_id = gc.classification_id
and gc.accession not in
(select BTRIM(unnest(string_to_array(alt_acc, ','))) as accession from go_classification_new
where alt_acc is not null)
and gc.accession not in
(select accession from go_classification_new);

