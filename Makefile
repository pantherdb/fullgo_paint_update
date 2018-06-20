### Working directory where files will be downloaded and built for each release (e.g. "06192018_fullgo") - Need to make into makefile argument
### should create new base folder derived from current date, unless base path argument is specified (for example, if incomplete update is continued on later dates)
### maybe we should just call this 'target', adhering to GO pipeline then rename after everything's done?
BASE_PATH ?= $(shell date +%Y-%m-%d)_fullgo
GAF_FILES_PATH = $(BASE_PATH)/gaf_files
########## GAF CREATION ##########
### -i property file with go and panther version.
GAF_PROFILE = "profile.txt"
### -d for the data folder from library
PTHR_DATA_DIR = "/auto/rcf-proj3/hm/mi/UPL/PANTHER13.1/data/"
### -a paint_annotation (from database)
ANNOT = "paint_annotation_datefix2"
### -q paint_annotation_qualifier (from database)
ANNOT_QUALIFIER = "paint_annotation_qualifier_semicolon"
### -g go_aggregate (from database)
GO_AGG = "go_aggregate_semicolon"
### -t TAIR10_TAIRlocusaccessionID_AGI_mapping.txt
TAIR_MAP = "/auto/rcf-proj3/hm/mi/PAINT/Analysis/TAIR10_TAIRlocusaccessionID_AGI_mapping.txt"
### -c evidence (from database)
EVIDENCE = "paint_evidence_semicolon"
### -T organism_taxon
TAXON = "organism_taxon"
### -G gene.dat in the DBload folder
GENE_DAT = "/auto/pmd-02/pdt/pdthomas/panther/xiaosonh/UPL/PANTHER13.1/library_building/DBload/gene.dat"
### -o output IBA gaf file folder
IBA_DIR = "IBA_GAFs"

download_fullgo:
	mkdir $(GAF_FILES_PATH)
	wget -r -l1 -nd --no-parent -P $(GAF_FILES_PATH) -A ".gz" http://geneontology.org/gene-associations/
	gunzip $(GAF_FILES_PATH)/*.gz
	wget -P $(BASE_PATH) http://geneontology.org/ontology/go.obo

extractfromgoobo:
	perl scripts/extractfromgoobo.pl -i $(BASE_PATH)/go.obo -o $(BASE_PATH)/inputforGOClassification.tsv > $(BASE_PATH)/obsolete_go_terms.txt
	wc -l $(BASE_PATH)/inputforGOClassification.tsv
	wc -l $(BASE_PATH)/obsolete_go_terms.txt

extractfromgoobo_relation:
	perl scripts/extractfromgoobo_relation.pl -i $(BASE_PATH)/go.obo -o $(BASE_PATH)/goparentchild.tsv
	wc -l $(BASE_PATH)/goparentchild.tsv

write_fullGoMappingPthr_slurm:
	echo "#!/bin/tcsh\n\
	#SBATCH --time=08:00:00\n\
	#SBATCH --ntasks=1\n\
	#SBATCH --mem=48gb\n\n\
	source /home/pmd-02/pdt/pdthomas/panther/cshrc.panther\n\n\
	perl $(shell pwd)/scripts/fullGoMappingPthr.pl \
	-f $(realpath $(GAF_FILES_PATH))/ \
	-t $(shell pwd)/scripts/pthr13_code_taxId.txt \
	-i /auto/pmd-02/pdt/pdthomas/panther/xiaosonh/UPL/PANTHER13.1/library_building/DBload/identifier.dat \
	-g /auto/pmd-02/pdt/pdthomas/panther/xiaosonh/UPL/PANTHER13.1/library_building/DBload/gene.dat \
	-o $(realpath $(BASE_PATH))/go.obo \
	-w $(realpath $(BASE_PATH))/Pthr_GO.tsv \
	-e $(realpath $(BASE_PATH))/PthrGOLog.txt" > $(BASE_PATH)/fullGoMappingPthr.slurm

create_gafs: paint_annotation, paint_evidence, paint_annotation_qualifier, go_aggregate, organism_taxon
	tcsh
	( perl createGAF.pl -i $(GAF_PROFILE) -d $(PTHR_DATA_DIR) -a $(ANNOT) -q $(ANNOT_QUALIFIER) -g $(GO_AGG) -t $(TAIR_MAP) -c $(EVIDENCE) -T $(TAXON) -G $(GENE_DAT) -o $(IBA_DIR) > IBD ) > & err &
	repair_gaf_symbols

paint_annotation:
	python3 scripts/db_caller.py scripts/sql/paint_annotation.sql > resources/$(ANNOT)

paint_annotation_qualifier:
	python3 scripts/db_caller.py scripts/sql/paint_annotation_qualifier.sql > resources/$(ANNOT_QUALIFIER)

paint_evidence:
	python3 scripts/db_caller.py scripts/sql/paint_evidence.sql > resources/$(EVIDENCE)

go_aggregate:
	python3 scripts/db_caller.py scripts/sql/go_aggregate.sql > resources/$(GO_AGG)

organism_taxon:
	python3 scripts/db_caller.py scripts/sql/organism_taxon.sql > resources/$(TAXON)

repair_gaf_symbols:
	wget ftp://ftp.pombase.org/nightly_update/misc/allNames.tsv -O resources/allNames.tsv
	wget ftp://ftp.pombase.org/nightly_update/misc/sysID2product.tsv -O resources/sysID2product.tsv
	perl scripts/fix_pombe_symbol.pl -i $(IBA_DIR)/gene_association.paint_pombase.gaf -p resources/allNames.tsv -d resources/sysID2product.tsv > gene_association.paint_pombase.fixed.gaf
