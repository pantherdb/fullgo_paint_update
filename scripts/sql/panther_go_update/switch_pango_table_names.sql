ALTER TABLE genelist_agg RENAME TO genelist_agg_old;
ALTER TABLE genelist_agg_new RENAME TO genelist_agg;
ALTER TABLE pango_version RENAME TO pango_version_old;
ALTER TABLE pango_version_new RENAME TO pango_version;
ALTER TABLE pango_go_classification RENAME TO pango_go_classification_old;
ALTER TABLE pango_go_classification_new RENAME TO pango_go_classification;
ALTER TABLE pango_go_classification_relationship RENAME TO pango_go_classification_relationship_old;
ALTER TABLE pango_go_classification_relationship_new RENAME TO pango_go_classification_relationship;