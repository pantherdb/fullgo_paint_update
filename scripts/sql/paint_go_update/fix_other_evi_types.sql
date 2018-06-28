-- insert into paint_evidence_fix tables with other paint_evidence_new table rows (with evidence_type other than 46 and 47)
set search_path = panther_upl;
insert into paint_evidence_fix
select * from paint_evidence_new
where evidence_type_sid not in (46, 47);

-- insert obsoleted type 46 and 47 evidence that not in paint_evidence_fix table into the paint_evidence_fix table, keep them obsoleted, just as a record
set search_path = panther_upl;
insert into paint_evidence_fix
select * from paint_evidence_new pe
where pe.evidence_type_sid in (46, 47)
and pe.obsolescence_date is not null
and not exists (select 1 from paint_evidence_fix pen where pe.evidence = pen.evidence and pe.annotation_id = pen.annotation_id and pe.evidence_type_sid = pen.evidence_type_sid);

-- insert non-obsoleted type 46 and 47 evidence that not in paint_evidence_fix table into the paint_evidence_fix table, make them obsoleted, just as a record for backup
set search_path = panther_upl;
insert into paint_evidence_fix (
            evidence_id, evidence_type_sid, classification_id, primary_object_id, 
            evidence, is_editable, created_by, creation_date, obsoleted_by, 
            obsolescence_date, updated_by, update_date, pathway_curation_id, 
            confidence_code_sid, annotation_id, protein_classification_id)
select evidence_id, evidence_type_sid, classification_id, primary_object_id, 
            evidence, is_editable, created_by, creation_date, 1, 
            now(), updated_by, update_date, pathway_curation_id, 
            confidence_code_sid, annotation_id, protein_classification_id
from (select * from paint_evidence_new pe
where pe.evidence_type_sid in (46, 47)
and pe.obsolescence_date is null
and not exists (select 1 from paint_evidence_fix pen where pe.evidence = pen.evidence and pe.annotation_id = pen.annotation_id and pe.evidence_type_sid = pen.evidence_type_sid)) x;