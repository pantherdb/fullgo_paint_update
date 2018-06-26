Truncate table panther.goanno_wf;
Copy panther.goanno_wf from '/pgres_data/data/Pthr_GO.tsv'
with null as '';

Truncate table panther.goobo_extract;
Copy panther.goobo_extract from '/pgres_data/data/inputforGOClassification.tsv'
with null as '' csv header delimiter '	';

Truncate table panther.goobo_parent_child;
Copy panther.goobo_parent_child from '/pgres_data/data/goparentchild.tsv'
with null as '' csv header delimiter '	';