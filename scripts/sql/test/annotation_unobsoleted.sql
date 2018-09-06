-- Should be a non-obsolete go_annotation for UniProtKB:Q5AD05 (CAL0000184565) to GO:0004784
set search_path = panther_upl;
select ga.* from gene g
join gene_node gn on gn.gene_id = g.gene_id
join go_annotation ga on ga.node_id = gn.node_id
join go_classification gc on gc.classification_id = ga.classification_id
where g.ext_db_gene_id = 'CAL0000184565'
and g.classification_version_sid = 24
and gc.accession = 'GO:0004784';