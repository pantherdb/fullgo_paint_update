--Update release dates in Fullgo_version table manually. go.obo contains information for GO related Columns 
	
ALTER TABLE fullgo_version_old RENAME TO fullgo_version_new;
Truncate table fullgo_version_new;
INSERT INTO fullgo_version_new(
        go_annotation_format_version, go_annotation_release_date, panther_version, 
        panther_release_date)
VALUES ('1.2', to_date('20180601','YYYYMMDD'), '13.1', 
        to_date('20180203','YYYYMMDD'));