include config.mk

### Working directory where files will be downloaded and built for each release (e.g. "2018-06-19_fullgo") - Need to make into makefile argument
### should create new base folder derived from current date, unless base path argument is specified (for example, if incomplete update is continued on later dates)
### maybe we should just call this 'target', adhering to GO pipeline then rename after everything's done?
export BASE_PATH ?= $(shell date +%Y-%m-%d)_fullgo
export FULL_BASE_PATH = $(shell realpath $(BASE_PATH))
export GAF_FILES_PATH = $(BASE_PATH)/gaf_files
export FULL_GAF_FILES_PATH = $(shell realpath $(GAF_FILES_PATH))
export PWD = $(shell pwd)
GO_VERSION_DATE ?= $(shell grep GO $(BASE_PATH)/profile.txt | head -n 1 | cut -f2 | sed 's/-//g')
export PANTHER_VERSION ?= 15.0
export GAF_VERSION ?= 2.1

ifeq ($(PANTHER_VERSION),13.1)
### PANTHER 13.1 ###
export PANTHER_VERSION_DATE = 20180203
export CLS_VER_ID = 24
export IDENTIFIER_PATH = /auto/pmd-02/pdt/pdthomas/panther/xiaosonh/UPL/PANTHER13.1/library_building/DBload/identifier.dat
export GENE_PATH = /auto/pmd-02/pdt/pdthomas/panther/xiaosonh/UPL/PANTHER13.1/library_building/DBload/gene.dat
export TAXON_ID_PATH = scripts/pthr13_code_taxId.txt
export NODE_PATH = /auto/pmd-02/pdt/pdthomas/panther/xiaosonh/UPL/PANTHER13.1/library_building/DBload/node.dat
export TREE_NODES_DIR = /auto/rcf-proj3/hm/mi/UPL/PANTHER13.1/data/treeNodes
else ifeq ($(PANTHER_VERSION),14.0)
### PANTHER 14.0 ###
export PANTHER_VERSION_DATE = 20181203
export CLS_VER_ID = 25
export IDENTIFIER_PATH = /auto/rcf-proj/hm/debert/PANTHER14.0/library_building/DBload/identifier.dat
export GENE_PATH = /auto/rcf-proj/hm/debert/PANTHER14.0/library_building/DBload/gene.dat
export TAXON_ID_PATH = scripts/pthr14_code_taxId.txt
else ifeq ($(PANTHER_VERSION),14.1)
export PANTHER_VERSION_DATE = 20190312
export CLS_VER_ID = 26
export IDENTIFIER_PATH = /auto/rcf-proj/hm/debert/PANTHER14.1/library_building/DBload/identifier.dat
export GENE_PATH = /auto/rcf-proj/hm/debert/PANTHER14.1/library_building/DBload/gene.dat
export TAXON_ID_PATH = scripts/pthr14_1_code_taxId.txt
export NODE_PATH = /auto/rcf-proj/hm/debert/PANTHER14.1/library_building/DBload/node.dat
export TREE_NODES_DIR = /auto/rcf-proj/hm/debert/PANTHER14.1/library_building/treeNodes
else ifeq ($(PANTHER_VERSION),15.0)
export PANTHER_VERSION_DATE = 20200214
export CLS_VER_ID = 27
export IDENTIFIER_PATH = /project/huaiyumi_14/hm/debert/PANTHER15.0/library_building/DBload/identifier.dat
export GENE_PATH = /project/huaiyumi_14/hm/debert/PANTHER15.0/library_building/DBload/gene.dat
export TAXON_ID_PATH = scripts/pthr15_code_taxId.txt
export NODE_PATH = /project/huaiyumi_14/hm/debert/PANTHER15.0/library_building/DBload/node.dat
export TREE_NODES_DIR = /project/huaiyumi_14/hm/debert/PANTHER15.0/library_building/treeNodes
else
export PANTHER_VERSION_DATE = 20201201
export CLS_VER_ID = 28
export IDENTIFIER_PATH = /project/huaiyumi_14/hm/debert/PANTHER16.0/library_building/target4/DBload/identifier.dat
export GENE_PATH = /project/huaiyumi_14/hm/debert/PANTHER16.0/library_building/target4/DBload/gene.dat
export TAXON_ID_PATH = scripts/pthr16_code_taxId.txt
export NODE_PATH = /project/huaiyumi_14/hm/debert/PANTHER16.0/library_building/target4/DBload/node.dat
export TREE_NODES_DIR = /project/huaiyumi_14/hm/debert/PANTHER16.0/library_building/target4/treeNodes
endif

########## GAF CREATION ##########
### -i property file with go and panther version.
export GAF_PROFILE = $(BASE_PATH)/profile.txt
### -d for the data folder from library
# PTHR_DATA_DIR = "/auto/rcf-proj3/hm/mi/UPL/PANTHER13.1/data/"
### -a paint_annotation (from database)
export ANNOT = paint_annotation
### -q paint_annotation_qualifier (from database)
export ANNOT_QUALIFIER = paint_annotation_qualifier
### -g go_aggregate (from database)
export GO_AGG = go_aggregate
### -t TAIR10_TAIRlocusaccessionID_AGI_mapping.txt
export TAIR_MAP = /auto/rcf-proj3/hm/mi/PAINT/Analysis/TAIR10_TAIRlocusaccessionID_AGI_mapping.txt
### -u Mapping to support "TAIR=locus" long IDs
export ARAPORT_MAP = resources/uniprot_to_araport_map_gaf.tsv
### -c evidence (from database)
export EVIDENCE = paint_evidence
### -T organism_taxon
export TAXON = organism_taxon
### -G gene.dat in the DBload folder
# GENE_DAT = "/auto/pmd-02/pdt/pdthomas/panther/xiaosonh/UPL/PANTHER13.1/library_building/DBload/gene.dat"
### -o output IBA gaf file folder
export IBA_DIR = $(BASE_PATH)/IBA_GAFs

### gen_iba_gaf_yamls variables ###
export GAF_GEN_A_DATA_TITLE = Before  # Before GO update - fullgo_version before table switch? Get from DB?
export GAF_GEN_A_CLS_VER_ID = $(CLS_VER_ID)  # 26
export GAF_GEN_A_IBA_DIR = $(BASE_PATH)/preupdate_data/IBA_GAFs
export GAF_GEN_B_DATA_TITLE = After  # After GO update
export GAF_GEN_B_CLS_VER_ID = $(CLS_VER_ID)  # 26
export GAF_GEN_B_IBA_DIR = $(IBA_DIR)

### PAINT annotation table version variables ###
export PAINT_ANNOT_A_TABLE = paint_annotation_old
export PAINT_ANNOT_B_TABLE = paint_annotation

download_fullgo:
	mkdir -p $(GAF_FILES_PATH)
	wget -r -l1 -nd --no-parent -P $(GAF_FILES_PATH) -A "gaf.gz" http://current.geneontology.org/annotations/
	wget -P $(GAF_FILES_PATH) http://current.geneontology.org/products/annotations/paint_other.gaf.gz
	wget -P $(BASE_PATH) http://current.geneontology.org/metadata/release-date.json
	wget -P $(BASE_PATH) http://current.geneontology.org/metadata/release-archive-doi.json
	envsubst < scripts/gunzip_gafs.slurm > $(BASE_PATH)/gunzip_gafs.slurm
	sbatch $(BASE_PATH)/gunzip_gafs.slurm
	wget -P $(BASE_PATH) http://current.geneontology.org/ontology/go.obo
	wget -P $(BASE_PATH) http://current.geneontology.org/ontology/extensions/go-plus.owl
	$(MAKE) make_profile
	$(MAKE) make_readme

extractfromgoobo:
	perl scripts/extractfromgoobo.pl -i $(BASE_PATH)/go.obo -o $(BASE_PATH)/inputforGOClassification.tsv > $(BASE_PATH)/obsolete_go_terms.txt
	wc -l $(BASE_PATH)/inputforGOClassification.tsv
	wc -l $(BASE_PATH)/obsolete_go_terms.txt
	perl scripts/extractfromgoobo_relation.pl -i $(BASE_PATH)/go.obo -o $(BASE_PATH)/goparentchild.tsv
	wc -l $(BASE_PATH)/goparentchild.tsv
	perl scripts/FindAllParents.pl $(BASE_PATH)/goparentchild.tsv $(BASE_PATH)/AllParentsofGOTerms.txt
	perl scripts/printHierarchy.pl $(BASE_PATH)/AllParentsofGOTerms.txt $(BASE_PATH)/FinalChildParent-Hierarchy.dat

split_fullGoMappingPthr_gafs:
	envsubst < scripts/mkdir_fullGoMappingPthr_groups.slurm > $(BASE_PATH)/mkdir_fullGoMappingPthr_groups.slurm
	sbatch --wait $(BASE_PATH)/mkdir_fullGoMappingPthr_groups.slurm

slurm_fullGoMappingPthr:
	NUMGROUPS=$(shell ls -d $(GAF_FILES_PATH)/group_* | wc -l) envsubst < scripts/fullGoMappingPthrHierarchy_para.slurm > $(BASE_PATH)/fullGoMappingPthrHierarchy_para_$(PANTHER_VERSION).slurm
	sbatch $(BASE_PATH)/fullGoMappingPthrHierarchy_para_$(PANTHER_VERSION).slurm

rm_partial_fullGoMappingPthr_files:
	rm $(BASE_PATH)/Pthr_GO_$(PANTHER_VERSION).tsv.*
	rm $(BASE_PATH)/GOWithHierarchy-CC-$(PANTHER_VERSION).dat.*
	rm $(BASE_PATH)/GOWithHierarchy-CC-$(PANTHER_VERSION).dat.*
	rm $(BASE_PATH)/GOWithHierarchy-CC-$(PANTHER_VERSION).dat.*

submit_fullGoMappingPthr_slurm:
	envsubst < scripts/fullGoMappingPthr.slurm > $(BASE_PATH)/fullGoMappingPthr_$(PANTHER_VERSION).slurm
	sbatch $(BASE_PATH)/fullGoMappingPthr_$(PANTHER_VERSION).slurm

submit_fullGoMappingPthrHierarchy_slurm:
	envsubst < scripts/fullGoMappingPthrHierarchy.slurm > $(BASE_PATH)/fullGoMappingPthrHierarchy_$(PANTHER_VERSION).slurm
	sbatch $(BASE_PATH)/fullGoMappingPthrHierarchy_$(PANTHER_VERSION).slurm

gaf2pmid_slurm:
	envsubst < scripts/gaf2pmid.slurm > $(BASE_PATH)/gaf2pmid.slurm
	sbatch $(BASE_PATH)/gaf2pmid.slurm
	# sed -e 's/^/http:\/\/amigo.geneontology.org\/amigo\/reference\//' $(BASE_PATH)/gaf2pmid_results > $(BASE_PATH)/gaf2pmid_result_urls

# Can't FTP from HPC
linkout_upload:
	grep 'PUBMED_HOST\|PUBMED_USERID\|PUBMED_PWORD' config/config.yaml | sed -e 's/:[^:\/\/]/="/g;s/$$/"/g;s/ *=/=/g' > $(BASE_PATH)/pubmed_upload_vars.txt
	@echo FULL_BASE_PATH=$(FULL_BASE_PATH) >> $(BASE_PATH)/pubmed_upload_vars.txt
	cat $(BASE_PATH)/pubmed_upload_vars.txt scripts/upload_links_to_pubmed.sh > $(BASE_PATH)/upload_links_to_pubmed.sh
	chmod 744 $(BASE_PATH)/upload_links_to_pubmed.sh
	./$(BASE_PATH)/upload_links_to_pubmed.sh

generate_go_hierarchy:
	envsubst < scripts/hierarchyfinalstep.slurm > $(BASE_PATH)/hierarchyfinalstep_$(PANTHER_VERSION).slurm
	sbatch $(BASE_PATH)/hierarchyfinalstep_$(PANTHER_VERSION).slurm

TaxonConstraintsLookup.txt:
	wget -P $(BASE_PATH) http://data.pantherdb.org/PANTHER15.0/globals/species_pthr15_annot.nhx
	ORGANISM_DAT=$(ORGANISM_DAT) envsubst < scripts/format_taxon_term_table.slurm > $(BASE_PATH)/format_taxon_term_table.slurm
	sbatch $(BASE_PATH)/format_taxon_term_table.slurm

get_fullgo_date:
	grep GO $(BASE_PATH)/profile.txt | head -n 1 | cut -f2

make_profile:
	python3 scripts/create_profile.py -j $(BASE_PATH)/release-date.json -d $(BASE_PATH)/release-archive-doi.json -p $(PANTHER_VERSION) > $(BASE_PATH)/profile.txt

make_profile_from_db:
	# query DB table fullgo_version - likely w/ python
	python3 scripts/make_profile_from_db.py $(BASE_PATH)/profile.txt

make_readme:
	echo "GO source files downloaded on $(shell date +%Y-%m-%d)" > $(BASE_PATH)/README

raw_table_count:
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther,goanno_wf
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther,goobo_extract
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther,goobo_parent_child

panther_table_count:
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther,go_classification
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther,go_classification_relationship
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther,fullgo_version
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther,genelist_agg

load_raw_go_to_panther:
	@echo "Counts of raw tables before data load:"
	$(MAKE) raw_table_count
	python3 scripts/db_caller.py scripts/sql/panther_go_update/load_raw_go.sql -v '{"panther_version": "$(PANTHER_VERSION)"}'
	@echo "Counts of raw tables after data load:"
	$(MAKE) raw_table_count

update_panther_new_tables:
	python3 scripts/db_caller.py scripts/sql/panther_go_update/go_classification.sql
	python3 scripts/db_caller.py scripts/sql/panther_go_update/fullgo_version.sql -v '{"go_release_date": "$(shell grep GO $(BASE_PATH)/profile.txt | head -n 1 | cut -f2 | sed 's/-//g')", "go_doi": "$(shell grep DOI $(BASE_PATH)/profile.txt | head -n 1 | cut -f2)", "panther_version": "$(PANTHER_VERSION)", "panther_version_date": "$(PANTHER_VERSION_DATE)"}'
	python3 scripts/db_caller.py scripts/sql/panther_go_update/genelist_agg.sql

switch_panther_table_names:
	@echo "Counts of panther tables before data load:"
	$(MAKE) panther_table_count
	python3 scripts/db_caller.py scripts/sql/panther_go_update/switch_table_names.sql
	@echo "Counts of panther tables after data load:"
	$(MAKE) panther_table_count
	$(MAKE) record_db_import_date

record_db_import_date:
	echo "Data imported into the PANTHER database on $(shell date +%Y-%m-%d)" | tee -a $(BASE_PATH)/README

check_dups:
	python3 scripts/db_caller.py scripts/sql/paint_go_update/go_classification_dups.sql

load_raw_go_to_paint:
	python3 scripts/db_caller.py scripts/sql/paint_go_update/load_raw_go.sql -v '{"panther_version": "$(PANTHER_VERSION)"}'

reset_paint_table:
	python3 scripts/db_caller.py scripts/sql/util/reset_paint_table.sql -v '{"table_name": "$(TABLE_NAME)"}'

update_paint_go_classification:
	python3 scripts/db_caller.py scripts/sql/paint_go_update/go_classification.sql
	# python3 scripts/db_caller.py scripts/sql/paint_go_update/go_classification_dups.sql	# Check for dups in relationship table?
	python3 scripts/db_caller.py scripts/sql/paint_go_update/fullgo_version.sql -v '{"go_release_date": "$(shell grep GO $(BASE_PATH)/profile.txt | head -n 1 | cut -f2 | sed 's/-//g')", "go_doi": "$(shell grep DOI $(BASE_PATH)/profile.txt | head -n 1 | cut -f2)", "panther_version": "$(PANTHER_VERSION)", "panther_version_date": "$(PANTHER_VERSION_DATE)"}'

regen_go_classification_relationship:	# Incorporated into go_classification.sql, so shouldn't need to be run ever again
	python3 scripts/db_caller.py scripts/sql/paint_go_update/go_classification_relationship.sql

update_paint_go_annotation:	# Could run up to an hour
	python3 scripts/db_caller.py scripts/sql/paint_go_update/go_annotation.sql

update_paint_go_evidence:
	python3 scripts/db_caller.py scripts/sql/paint_go_update/go_evidence.sql

update_paint_go_annot_qualifier:
	python3 scripts/db_caller.py scripts/sql/paint_go_update/go_annotation_qualifier.sql

update_paint_paint_annotation:
	python3 scripts/db_caller.py scripts/sql/paint_go_update/paint_annotation.sql

update_paint_paint_evidence:
	python3 scripts/db_caller.py scripts/sql/paint_go_update/paint_evidence.sql

update_paint_paint_evidence_new:
	python3 scripts/db_caller.py -n scripts/sql/paint_go_update/update_paint_evidence/get_exp_annots.sql > $(BASE_PATH)/resources/exp_annots.txt
	python3 scripts/db_caller.py -n scripts/sql/paint_go_update/update_paint_evidence/get_paint_evs.sql > $(BASE_PATH)/resources/paint_evs.txt
	python3 scripts/obsolete_p_evidence.py -g $(BASE_PATH)/resources/exp_annots.txt -p $(BASE_PATH)/resources/paint_evs.txt

update_paint_paint_annot_qualifier:
	python3 scripts/db_caller.py scripts/sql/paint_go_update/paint_annotation_qualifier.sql

update_comments_status:
	python3 scripts/db_caller.py scripts/sql/paint_go_update/comments_status_term_obsoleted.sql
	python3 scripts/db_caller.py scripts/sql/paint_go_update/comments_status_term_not_obsoleted.sql
	python3 scripts/db_caller.py scripts/sql/paint_go_update/comments_status_lost_leaf_annots.sql	### SET CORRECT DATE IN THIS SCRIPT BEFORE RUNNING (SHOULD BE DATE OF paint_annotation TABLE UPDATE)
	python3 scripts/db_caller.py scripts/sql/paint_go_update/comments_status_unobsoleted_ibds.sql

obsolete_redundant_ibds: setup_directories
	mkdir -p $(BASE_PATH)/resources/sql/cache
	python3 scripts/obsolete_redundant_ibds.py /home/pmd-02/pdt/pdthomas/panther/famlib/rel/PANTHER$(PANTHER_VERSION) _new $(BASE_PATH)/resources/sql/cache/obsolete_redundant_ibds.txt

switch_evidence_to_pmid:
	python3 scripts/db_caller.py scripts/sql/paint_go_update/switch_evidence_to_pmid.sql

delete_incorrect_go_annot_qualifiers:
	python3 scripts/db_caller.py scripts/sql/paint_go_update/delete_incorrect_go_annot_qualifiers.sql

run_restore_annots:
	python3 scripts/db_caller.py scripts/sql/paint_go_update/fix_leaf_node_annots.sql
	python3 scripts/db_caller.py scripts/sql/paint_go_update/fix_leaf_node_comments.sql
	python3 scripts/db_caller.py scripts/sql/paint_go_update/fix_anc_node_annots.sql
	python3 scripts/db_caller.py scripts/sql/paint_go_update/fix_anc_node_comments.sql
	python3 scripts/db_caller.py scripts/sql/paint_go_update/fix_other_evi_types.sql

paint_go_table_counts:
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther_upl,go_classification
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther_upl,go_classification_relationship
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther_upl,go_evidence
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther_upl,go_annotation
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther_upl,go_annotation_qualifier

paint_table_counts:
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther_upl,go_classification
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther_upl,go_classification_relationship
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther_upl,go_evidence
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther_upl,go_annotation
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther_upl,go_annotation_qualifier
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther_upl,paint_annotation
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther_upl,paint_evidence
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther_upl,curation_status
	python3 scripts/db_caller.py scripts/sql/table_count.sql -v panther_upl,comments

backup_paint_tables:
	# Use /usr/pgsql-9.6/bin/pg_dump on 207.151.20.155. There's a version mismatch with pg_dump in path.
	pg_dump -d Curation -t panther_upl.go_classification --username postgres > go_classification.dump
	pg_dump -d Curation -t panther_upl.go_classification_relationship --username postgres > go_classification_relationship.dump
	pg_dump -d Curation -t panther_upl.go_evidence --username postgres > go_evidence.dump
	pg_dump -d Curation -t panther_upl.go_annotation --username postgres > go_annotation.dump
	pg_dump -d Curation -t panther_upl.go_annotation_qualifier --username postgres > go_annotation_qualifier.dump
	pg_dump -d Curation -t panther_upl.paint_annotation --username postgres > paint_annotation.dump
	pg_dump -d Curation -t panther_upl.paint_evidence --username postgres > paint_evidence.dump
	pg_dump -d Curation -t panther_upl.curation_status --username postgres > curation_status.dump
	pg_dump -d Curation -t panther_upl.comments --username postgres > comments.dump

refresh_paint_panther_upl:
	/usr/pgsql-9.4/bin/pg_dumpall -U postgres --roles-only -f /pgres_log/db_roles.dump
	pg_dump -U postgres -d Curation --schema-only -f /pgres_log/Curation.schema.dump
	pg_dump -U postgres -d Curation -n panther_upl -f /pgres_log/Curation.panther_upl.dump
	# in psql on target server: create database "Curation"; # if missing
	# psql Curation < /pgdata/pgsql/data/db_roles.dump
	# psql Curation < /pgdata/pgsql/data/Curation.schema.dump
	# Cleaner to DROP SCHEMA panther_upl CASCADE; before loading data dump
	# psql Curation < /pgdata/pgsql/data/Curation.panther_upl.dump
	# Also need to REFRESH MATERIALIZED VIEW for go_aggregate and paint_aggregate
	# Run create_raw_go_tables.sql in pgAdmin

paint_error_srv_check:
	perl scripts/paintErrorCheck.pl resources/book_list_13.1.txt "http://panthercuration.usc.edu/webservices/family.jsp?searchValue=book_var&searchType=SEARCH_TYPE_AGG_FAMILY_ANNOTATION_INFO" > $(BASE_PATH)/paint_error_check.xml
	python3 scripts/paint_xml_parser.py $(BASE_PATH)/paint_error_check.xml > $(BASE_PATH)/parsed_paint_srv_results

switch_paint_table_names:
	@echo "Counts of paint tables before table switch:"
	$(MAKE) paint_table_counts
	python3 scripts/db_caller.py scripts/sql/paint_go_update/switch_table_names.sql
	@echo "Counts of paint tables after table switch:"
	$(MAKE) paint_table_counts

switch_table_names_go_only:
	$(MAKE) paint_go_table_counts
	python3 scripts/db_caller.py scripts/sql/paint_go_update/switch_table_names_go_only.sql
	$(MAKE) paint_go_table_counts

regenerate_go_aggregate_view:
	python3 scripts/db_caller.py scripts/sql/paint_go_update/regenerate_go_aggregate_view.sql

regenerate_paint_aggregate_view:
	python3 scripts/db_caller.py scripts/sql/paint_go_update/regenerate_paint_aggregate_view.sql

reset_paint_table_names:
	@echo "Counts of paint tables before table switch:"
	$(MAKE) paint_table_counts
	python3 scripts/db_caller.py scripts/sql/paint_go_update/reset_table_names.sql
	@echo "Counts of paint tables after table switch:"
	$(MAKE) paint_table_counts

# update_taxon_constraints_file:

setup_preupdate_data: $(BASE_PATH)/resources/panther_blacklist.txt $(BASE_PATH)/resources/complex_terms.tsv
	mkdir -p $(BASE_PATH)/preupdate_data/resources
	# Retain previous GO version for accuracy
	$(MAKE) BASE_PATH=$(BASE_PATH)/preupdate_data make_profile_from_db
	# Reuse panther_blacklist.txt cuz it takes sooo long to make
	ln -sf $(realpath $(BASE_PATH)/resources/panther_blacklist.txt) $(BASE_PATH)/preupdate_data/resources/panther_blacklist.txt
	ln -sf $(realpath $(BASE_PATH)/resources/complex_terms.tsv) $(BASE_PATH)/preupdate_data/resources/complex_terms.tsv
	# Generate IBA GAFs from preupdate data - call before table name switch
	$(MAKE) BASE_PATH=$(BASE_PATH)/preupdate_data create_gafs

# Run this after both GAF sets generated
gen_iba_gaf_yamls:
	# Need to query "before" resource files (go_aggregate, paint_annotation, etc.)
	envsubst < resources/iba_gaf_gen_a.yaml > $(BASE_PATH)/iba_gaf_gen_a.yaml
	envsubst < resources/iba_gaf_gen_b.yaml > $(BASE_PATH)/iba_gaf_gen_b.yaml

create_gafs: setup_directories pombe_sources paint_annotation paint_evidence paint_annotation_qualifier organism_taxon go_aggregate	# must run from tcsh shell
	# Slurm this
	envsubst < scripts/createGAF.slurm > $(BASE_PATH)/createGAF.slurm
	sbatch $(BASE_PATH)/createGAF.slurm

setup_directories:
	mkdir -p $(BASE_PATH)/resources
	mkdir -p $(IBA_DIR)

%resources/panther_blacklist.txt: %resources/uniprot_protein.gpi.ids
	R_DIR=$*resources envsubst < scripts/create_panther_gene_blacklist.slurm > $*create_panther_gene_blacklist.slurm
	sbatch --wait $*create_panther_gene_blacklist.slurm

.PRECIOUS: %resources/uniprot_protein.gpi.ids
%resources/uniprot_protein.gpi.ids:
	mkdir -p $*resources
	wget ftp://ftp.ebi.ac.uk/pub/contrib/goa/uniprot_protein.gpi.gz -O $*resources/uniprot_protein.gpi.gz
	R_DIR=$*resources envsubst < scripts/cut_uniprot_ids.slurm > $*cut_uniprot_ids.slurm
	sbatch --wait $*cut_uniprot_ids.slurm

.PRECIOUS: %/resources/complex_terms.tsv
%/resources/complex_terms.tsv:
	envsubst < scripts/robot_complex_terms.slurm > $*/robot_complex_terms.slurm
	sbatch --wait $*/robot_complex_terms.slurm

paint_annotation:
	python3 scripts/db_caller.py scripts/sql/paint_annotation.sql -o $(BASE_PATH)/resources/$(ANNOT)

paint_annotation_qualifier:
	python3 scripts/db_caller.py scripts/sql/paint_annotation_qualifier.sql -o $(BASE_PATH)/resources/$(ANNOT_QUALIFIER)

paint_evidence:
	python3 scripts/db_caller.py scripts/sql/paint_evidence.sql -o $(BASE_PATH)/resources/$(EVIDENCE)

go_aggregate:
	python3 scripts/db_caller.py scripts/sql/go_aggregate.sql -o $(BASE_PATH)/resources/$(GO_AGG)

organism_taxon:
	python3 scripts/db_caller.py scripts/sql/organism_taxon.sql -o $(BASE_PATH)/resources/$(TAXON)

pombe_sources:
	wget ftp://ftp.pombase.org/nightly_update/misc/allNames.tsv -O $(BASE_PATH)/resources/allNames.tsv
	wget ftp://ftp.pombase.org/nightly_update/misc/sysID2product.tsv -O $(BASE_PATH)/resources/sysID2product.tsv

# Now in createGAF.slurm
repair_gaf_symbols:
	perl scripts/fix_pombe_symbol.pl -i $(IBA_DIR)/gene_association.paint_pombase.gaf -p $(BASE_PATH)/resources/allNames.tsv -d $(BASE_PATH)/resources/sysID2product.tsv > $(IBA_DIR)/gene_association.paint_pombase.gaf
	# cp $(BASE_PATH)/gene_association.paint_pombase.fixed.gaf $(IBA_DIR)/gene_association.paint_pombase.gaf

run_reports:
	mkdir -p scripts/sql/cache/
	python3 scripts/iba_count.py --a_yaml $(BASE_PATH)/iba_gaf_gen_a.yaml --b_yaml $(BASE_PATH)/iba_gaf_gen_b.yaml
	diff -u $(BASE_PATH)/preupdate_data/affected_ibas.gaf $(BASE_PATH)/affected_ibas.gaf | grep -E "^\-" > $(BASE_PATH)/dropped_ibas_filtered_raw
	grep -v "Created on" $(BASE_PATH)/dropped_ibas_filtered_raw | grep -v "$(BASE_PATH)" | sed 's/^-//' > $(BASE_PATH)/dropped_IBAs_filtered
	python3 scripts/iba_count.py --a_yaml $(BASE_PATH)/iba_gaf_gen_a.yaml --b_yaml $(BASE_PATH)/iba_gaf_gen_b.yaml --mods_only
	python3 scripts/version_paint_annot_counts.py --a_yaml $(BASE_PATH)/iba_gaf_gen_a.yaml --b_yaml $(BASE_PATH)/iba_gaf_gen_b.yaml --reload_data
	python3 scripts/report_curation_status.py

	# Ex: python3 scripts/created_ibds_by_curator.py -b 2020-01-31 -a 2020-03-26 -p
	python3 scripts/created_ibds_by_curator.py -b $(BEFORE_DATE) -a $(AFTER_DATE) -p
	# Download and/or point to release folders. Ex: ftp://ftp.pantherdb.org/downloads/paint/14.1/2020-01-31/ and 2020-01-31
	envsubst < scripts/compare_paint_releases.slurm > $(BASE_PATH)/compare_paint_releases.slurm
	sbatch --wait $(BASE_PATH)/compare_paint_releases.slurm
	python3 scripts/publish_sheet_json.py -t $(shell date +%Y-%m-%d)_update_stats -j $(BASE_PATH)/update_stats.json

push_gafs_to_ftp:
	@echo "Needs to be implemented"

leaf_species_list:
	python3 scripts/db_caller.py -n scripts/sql/util/leaf_species_list.sql