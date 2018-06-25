ALTER TABLE genelist_agg_old RENAME TO genelist_agg_new;					
Truncate table genelist_agg_new;					
INSERT INTO genelist_agg_new(gene_id, gene_name, gene_symbol, genex_assay, snp_assay, panther_best_hit, panther_best_hit_name, panther_best_hit_acc, panther_best_hit_score, panther_mf, panther_bp, transcripts, proteins, cytoband, cytoband_sort, species, genelist_rowuid, cra_chromosome, cra_start_pos, cra_end_pos, pub_chromosome, pub_start_pos, pub_end_pos, source_id, gene_ext_id, gene_ext_acc, cra_chromosome_rank, pub_chromosome_rank, pathway, panther_cc, panther_pc, public_id, reactome) SELECT  gene_id, gene_name, gene_symbol, genex_assay, snp_assay, panther_best_hit, panther_best_hit_name, panther_best_hit_acc, panther_best_hit_score, panther_mf, panther_bp, transcripts, proteins, cytoband, cytoband_sort, species, genelist_rowuid, cra_chromosome, cra_start_pos, cra_end_pos, pub_chromosome, pub_start_pos, pub_end_pos, source_id, gene_ext_id, gene_ext_acc, cra_chromosome_rank, pub_chromosome_rank, pathway, panther_cc, panther_pc, public_id, reactome FROM   genelist_agg WHERE  gene_id IS NOT NULL;

update genelist_agg_new g set fullgo_mf_comp = m.godetails
from ( 
    select gw.geneid, string_agg(distinct gw.go_acc, ',') as godetails 
    from goanno_wf gw, go_classification_new gc, classification_term_type ct 
    where (gw.qualifier <> 'NOT' or gw.qualifier is null) and gw.go_acc = gc.accession and gc.obsolescence_date is null and gc.term_type_sid = ct.term_type_sid and ct.term_name = 'molecular_function' group by 1 ) m 
where g.gene_ext_acc = m.geneid;

update genelist_agg_new g set fullgo_cc_comp = m.godetails 
from (
    select gw.geneid, string_agg(distinct gw.go_acc, ',') as godetails 
    from goanno_wf gw, go_classification_new gc, classification_term_type ct 
    where (gw.qualifier <> 'NOT' or gw.qualifier is null) and gw.go_acc = gc.accession and gc.obsolescence_date is null and gc.term_type_sid = ct.term_type_sid and ct.term_name = 'cellular_component' group by 1) m 
where g.gene_ext_acc = m.geneid;

update genelist_agg_new g set fullgo_bp_comp = m.godetails 
from ( 
    select gw.geneid, string_agg(distinct gw.go_acc, ',') as godetails 
    from goanno_wf gw, go_classification_new gc, classification_term_type ct 
where (gw.qualifier <> 'NOT' or gw.qualifier is null) and gw.go_acc = gc.accession and gc.obsolescence_date is null and gc.term_type_sid = ct.term_type_sid and ct.term_name = 'biological_process' group by 1) m where g.gene_ext_acc = m.geneid;