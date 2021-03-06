-- change the table names for the new table to be accessible by paint server and tool
set search_path=panther_upl;
ALTER TABLE go_classification RENAME TO go_classification_old;
ALTER TABLE go_classification_new RENAME TO go_classification;
ALTER TABLE go_classification_relationship RENAME TO go_classification_relationship_old;
ALTER TABLE go_classification_relationship_new RENAME TO go_classification_relationship;
ALTER TABLE fullgo_version RENAME TO fullgo_version_old;
ALTER TABLE fullgo_version_new RENAME TO fullgo_version;
ALTER TABLE go_evidence RENAME TO go_evidence_old;
ALTER TABLE go_evidence_new RENAME TO go_evidence;
ALTER TABLE go_annotation RENAME TO go_annotation_old;
ALTER TABLE go_annotation_new RENAME TO go_annotation;
ALTER TABLE go_annotation_qualifier RENAME TO go_annotation_qualifier_old;
ALTER TABLE go_annotation_qualifier_new RENAME TO go_annotation_qualifier;
ALTER TABLE go_evidence_qualifier RENAME TO go_evidence_qualifier_old;
ALTER TABLE go_evidence_qualifier_new RENAME TO go_evidence_qualifier;