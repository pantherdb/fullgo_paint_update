select organism, short_name, taxon_id from panther_upl.organism
where classification_version_sid = {classification_version_sid};