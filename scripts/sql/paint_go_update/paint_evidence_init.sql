--copy data to new table to be updated, old table serve as a backup, try to keep the evidence_id that didn't change
set search_path = panther_upl;
--due to the _fix table switcheroos the _new tables will always be hanging around
ALTER TABLE paint_evidence_old RENAME TO paint_evidence_new;
truncate table paint_evidence_new;
insert into paint_evidence_new select * from paint_evidence;