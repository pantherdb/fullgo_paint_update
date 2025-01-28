--Update release dates in pango_version table manually. go.obo contains information for GO related Columns 
	
ALTER TABLE pango_version_old RENAME TO pango_version_new;
Truncate table pango_version_new;
INSERT INTO pango_version_new(
        go_annotation_format_version, go_annotation_release_date, go_annotation_doi, pango_version, 
        pango_release_date)
VALUES ('1.2', to_date('{go_release_date}','YYYYMMDD'), '{go_doi}', '{pango_version}', 
        to_date('{pango_version_date}','YYYYMMDD'));