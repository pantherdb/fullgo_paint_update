ALTER TABLE panther.genelist_agg_old RENAME TO genelist_agg_new;					
Truncate table panther.genelist_agg_new;					
INSERT INTO panther.genelist_agg_new(gene_id, gene_name, gene_symbol, genex_assay, snp_assay, panther_best_hit, panther_best_hit_name, 
    panther_best_hit_acc, panther_best_hit_score, panther_mf, panther_bp, transcripts, proteins, cytoband, cytoband_sort, species, 
    genelist_rowuid, cra_chromosome, cra_start_pos, cra_end_pos, pub_chromosome, pub_start_pos, pub_end_pos, source_id, gene_ext_id, 
    gene_ext_acc, cra_chromosome_rank, pub_chromosome_rank, pathway, panther_cc, panther_pc, public_id, reactome, fullgo_mf_comp, 
    fullgo_cc_comp, fullgo_bp_comp, fullgo_mf_exp, fullgo_cc_exp, fullgo_bp_exp) 
    SELECT  gene_id, gene_name, gene_symbol, genex_assay, snp_assay, panther_best_hit, panther_best_hit_name, panther_best_hit_acc, 
    panther_best_hit_score, panther_mf, panther_bp, transcripts, proteins, cytoband, cytoband_sort, species, genelist_rowuid, 
    cra_chromosome, cra_start_pos, cra_end_pos, pub_chromosome, pub_start_pos, pub_end_pos, source_id, gene_ext_id, gene_ext_acc, 
    cra_chromosome_rank, pub_chromosome_rank, pathway, panther_cc, panther_pc, public_id, reactome, fullgo_mf_comp, fullgo_cc_comp, 
    fullgo_bp_comp, fullgo_mf_exp, fullgo_cc_exp, fullgo_bp_exp
    FROM   panther.genelist_agg WHERE  gene_id IS NOT NULL;
reindex table panther.genelist_agg_new;

update panther.genelist_agg_new g set pango_mf_iba = m.godetails
from ( 
    select gw.geneid, string_agg(distinct gw.go_acc, ',') as godetails 
    from panther.goanno_wf gw, panther.pango_go_classification_new gc, panther.classification_term_type ct 
    where (gw.qualifier <> 'NOT' or gw.qualifier is null) and gw.go_acc = gc.accession and gc.obsolescence_date is null and gc.term_type_sid = ct.term_type_sid and ct.term_name = 'molecular_function' 
    and gw.confidence_code in ('IBA')
    group by 1 ) m 
where g.gene_ext_acc = m.geneid;

update panther.genelist_agg_new g set pango_cc_iba = m.godetails 
from (
    select gw.geneid, string_agg(distinct gw.go_acc, ',') as godetails 
    from panther.goanno_wf gw, panther.pango_go_classification_new gc, panther.classification_term_type ct 
    where (gw.qualifier <> 'NOT' or gw.qualifier is null) and gw.go_acc = gc.accession and gc.obsolescence_date is null and gc.term_type_sid = ct.term_type_sid and ct.term_name = 'cellular_component' 
    and gw.confidence_code in ('IBA')
    group by 1) m 
where g.gene_ext_acc = m.geneid;

update panther.genelist_agg_new g set pango_bp_iba = m.godetails 
from ( 
    select gw.geneid, string_agg(distinct gw.go_acc, ',') as godetails 
    from panther.goanno_wf gw, panther.pango_go_classification_new gc, panther.classification_term_type ct 
    where (gw.qualifier <> 'NOT' or gw.qualifier is null) and gw.go_acc = gc.accession and gc.obsolescence_date is null and gc.term_type_sid = ct.term_type_sid and ct.term_name = 'biological_process' 
    and gw.confidence_code in ('IBA')
    group by 1) m 
where g.gene_ext_acc = m.geneid;
