--Update release dates in Fullgo_version table manually. go.obo contains information for GO related Columns 
	
ALTER TABLE panther_upl.fullgo_version_old RENAME TO fullgo_version_new;
Truncate table panther_upl.fullgo_version_new;
INSERT INTO panther_upl.fullgo_version_new(
        go_annotation_format_version, go_annotation_release_date, panther_version, 
        panther_release_date)
VALUES ('1.2', to_date('{go_release_date}','YYYYMMDD'), '{panther_version}', 
        to_date('{panther_version_date}','YYYYMMDD'));