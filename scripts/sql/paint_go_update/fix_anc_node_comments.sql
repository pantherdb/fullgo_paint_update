-- insert a row with the status 'require paint review' for panther families that obsoleted paint_annotation_new due to above method into the curation_status_new. 
set search_path = panther_upl;
INSERT INTO curation_status_new(
            curation_status_id, status_type_sid, classification_id, user_id, 
            creation_date)
SELECT nextval('uids'), 7, X.classification_id, 1113, now()
from (SELECT distinct cls.classification_id
from paint_evidence_new pe, paint_annotation_fix pan, node n, classification cls, paint_annotation_new pa
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 47
and not exists (select 1 from paint_evidence_fix pen where pan.annotation_id = pen.annotation_id and pen.evidence_type_sid = 47)
and pan.annotation_id = pa.annotation_id
and pa.obsolescence_date is null
and pan.node_id = n.node_id
and n.classification_version_sid = 24
and split_part(n.accession,':',1)=cls.accession
and cls.classification_version_sid = 24
and cls.depth = 5) X;

-- insert a row with the status 'require paint review' for panther families that un-obsoleted paint_annotation_new due to above method into the curation_status_new.  
set search_path = panther_upl;
INSERT INTO curation_status_new(
            curation_status_id, status_type_sid, classification_id, user_id, 
            creation_date)
SELECT nextval('uids'), 7, X.classification_id, 1113, now()
from (SELECT distinct cls.classification_id
from paint_evidence_new pe, paint_annotation_fix pan, node n, classification cls, paint_annotation_new pa
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 47
and exists (select 1 from paint_evidence_fix pen where pan.annotation_id = pen.annotation_id and pen.evidence_type_sid = 47)
and pan.annotation_id = pa.annotation_id
and pa.obsolescence_date is not null
and pa.obsoleted_by = 1
and pan.node_id = n.node_id
and n.classification_version_sid = 24
and split_part(n.accession,':',1)=cls.accession
and cls.classification_version_sid = 24
and cls.depth = 5) X;

-- update comments_new table
set search_path = panther_upl;
update comments_new cm
set remark = cm.remark || '\n' || current_date || ': PAINT_ANCESTOR annotation to node ' || x.public_id || ' with ' || x.go_term || ' was obsoleted because there was no supporting ancesotr node paint annotation left after PANTHER library version update.\n'
from (SELECT distinct cls.classification_id, n.public_id, gc.accession go_term
from paint_evidence_new pe, paint_annotation_fix pan, node n, classification cls, go_classification gc, paint_annotation_new pa
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 47
and not exists (select 1 from paint_evidence_fix pen where pan.annotation_id = pen.annotation_id and pen.evidence_type_sid = 47)
and pan.annotation_id = pa.annotation_id
and pa.obsolescence_date is null
and pan.node_id = n.node_id
and n.classification_version_sid = 24
and split_part(n.accession,':',1)=cls.accession
and cls.classification_version_sid = 24
and cls.depth = 5
and pan.classification_id = gc.classification_id) x
where cm.classification_id = x.classification_id;

set search_path = panther_upl;
insert into comments_new (comment_id, classification_id, protein_id, remark, created_by, 
            creation_date, obsoleted_by, obsolescence_date, node_id)
select nextval('uids'), x.classification_id, null, current_date || ': PAINT_EXP annotation to node ' || x.public_id || ' with ' || x.go_term || ' was obsoleted because there was no supporting leaf node experimental go annotation left after PANTHER library version update.\n', 1113, current_date, null, null, null
from (SELECT distinct cls.classification_id, n.public_id, gc.accession go_term
from paint_evidence_new pe, paint_annotation_fix pan, node n, classification cls, go_classification gc, paint_annotation_new pa
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 47
and not exists (select 1 from paint_evidence_fix pen where pan.annotation_id = pen.annotation_id and pen.evidence_type_sid = 47)
and pan.annotation_id = pa.annotation_id
and pa.obsolescence_date is null
and pan.node_id = n.node_id
and n.classification_version_sid = 24
and split_part(n.accession,':',1)=cls.accession
and cls.classification_version_sid = 24
and cls.depth = 5
and pan.classification_id = gc.classification_id) x
where not exists (
select 1 from comments_new cm
where cm.classification_id = x.classification_id);

set search_path = panther_upl;
update comments_new cm
set remark = cm.remark || '\n' || current_date || ': PAINT_ANCESTOR annotation to node ' || x.public_id || ' with ' || x.go_term || ' was un-obsoleted because there exists now supporting ancesotr node paint annotation after PANTHER library version update.\n'
from (SELECT distinct cls.classification_id, n.public_id, gc.accession go_term
from paint_evidence_new pe, paint_annotation_fix pan, node n, classification cls, go_classification gc, paint_annotation_new pa
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 47
and exists (select 1 from paint_evidence_fix pen where pan.annotation_id = pen.annotation_id and pen.evidence_type_sid = 47)
and pan.annotation_id = pa.annotation_id
and pa.obsolescence_date is not null
and pa.obsoleted_by = 1
and pan.node_id = n.node_id
and n.classification_version_sid = 24
and split_part(n.accession,':',1)=cls.accession
and cls.classification_version_sid = 24
and cls.depth = 5
and pan.classification_id = gc.classification_id) x
where cm.classification_id = x.classification_id;

set search_path = panther_upl;
insert into comments_new (comment_id, classification_id, protein_id, remark, created_by, 
            creation_date, obsoleted_by, obsolescence_date, node_id)
select nextval('uids'), x.classification_id, null, current_date || ': PAINT_EXP annotation to node ' || x.public_id || ' with ' || x.go_term || ' was un-obsoleted because there exists now supporting leaf node experimental go annotation after PANTHER library version update.\n', 1113, current_date, null, null, null
from (SELECT distinct cls.classification_id, n.public_id, gc.accession go_term
from paint_evidence_new pe, paint_annotation_fix pan, node n, classification cls, go_classification gc, paint_annotation_new pa
where pan.annotation_id = pe.annotation_id
and pe.evidence_type_sid = 47
and exists (select 1 from paint_evidence_fix pen where pan.annotation_id = pen.annotation_id and pen.evidence_type_sid = 47)
and pan.annotation_id = pa.annotation_id
and pa.obsolescence_date is not null
and pa.obsoleted_by = 1
and pan.node_id = n.node_id
and n.classification_version_sid = 24
and split_part(n.accession,':',1)=cls.accession
and cls.classification_version_sid = 24
and cls.depth = 5
and pan.classification_id = gc.classification_id) x
where not exists (
select 1 from comments_new cm
where cm.classification_id = x.classification_id);