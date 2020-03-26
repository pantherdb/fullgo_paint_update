Truncate table panther_upl.goanno_wf;
Copy panther_upl.goanno_wf from '{load_dir}Pthr_GO_{panther_version}.tsv'
with null as '';

Truncate table panther_upl.goobo_extract;
Copy panther_upl.goobo_extract from '{load_dir}inputforGOClassification.tsv'
with null as '' csv header delimiter '	';

Truncate table panther_upl.goobo_parent_child;
Copy panther_upl.goobo_parent_child from '{load_dir}goparentchild.tsv'
with null as '' csv header delimiter '	';