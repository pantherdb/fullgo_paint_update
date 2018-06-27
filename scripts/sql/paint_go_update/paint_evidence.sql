--copy data to new table to be updated, old table serve as a backup, try to keep the evidence_id that didn't change
set search_path = panther_upl;
ALTER TABLE paint_evidence_old RENAME TO paint_evidence_new;
truncate table paint_evidence_new;
insert into paint_evidence_new select * from paint_evidence;

--Go through the paint_evidence table, for all evidence type as 46 (paint EXP), the evidence can be forwardly tracked to go_annotation entries with obsolescence_date as null in full GO annotation table. If not, mark the evidence as obsoleted.
set search_path = panther_upl;
update paint_evidence_new pen 
set obsoleted_by = 1, obsolescence_date = now() 
where not exists ( 
    select 1 from go_annotation_new gan 
    where cast(pen.evidence as int) = gan.annotation_id 
    and gan.obsolescence_date is null
  ) 
  and pen.evidence_type_sid = 46 
  and pen.obsolescence_date is null;

-- Go through the paint-annotation table, and see if this annotation_id is still exist in the paint_evidence table with obsoleted_by column is null, if not, obsolete the paint_annotation entry
set search_path=panther_upl;
update paint_annotation_new pa 
set obsoleted_by = 1, obsolescence_date = now() 
from paint_evidence_new pe 
where pa.annotation_id not in (
    select pe.annotation_id 
    from paint_evidence_new pe, paint_annotation_new pa 
    where pe.annotation_id = pa.annotation_id 
    and pe.evidence_type_sid = 46 
    and pe.obsoleted_by is null
  ) 
  and pa.annotation_id = pe.annotation_id 
  and pe.evidence_type_sid = 46 
  and pa.obsolescence_date is null;