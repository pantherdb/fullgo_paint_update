Truncate table panther.goanno_wf;
Copy panther.goanno_wf from '{load_dir}Pthr_GO_{panther_version}.tsv'
with null as '';
reindex table panther.goanno_wf;

Truncate table panther.goobo_extract;
Copy panther.goobo_extract from '{load_dir}inputforGOClassification.tsv'
with null as '' csv header delimiter '	';

Truncate table panther.goobo_parent_child;
Copy panther.goobo_parent_child from '{load_dir}goparentchild.tsv'
with null as '' csv header delimiter '	';