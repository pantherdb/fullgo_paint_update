--There are 'PAINT_REF' (evidence_type_sid = 41) type evidence in go_evidence table that cause problems for Anushya's code. A temporary fix is to changed evidence_type_sid column from 41 ('PAINT_REF') to 26 ('PMID') and evidence column to '21873635'.
set search_path = panther_upl;
update go_evidence_new ge
set evidence_type_sid = 26, -- "PMID" 
evidence = '21873635'
where evidence_type_sid = 41;