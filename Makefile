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

create_gafs: paint_annotation, paint_evidence, paint_annotation_qualifier, go_aggregate, organism_taxon
	tcsh
	( perl createGAF.pl -i $(GAF_PROFILE) -d $(PTHR_DATA_DIR) -a $(ANNOT) -q $(ANNOT_QUALIFIER) -g $(GO_AGG) -t $(TAIR_MAP) -c $(EVIDENCE) -T $(TAXON) -G $(GENE_DAT) -o $(IBA_DIR) > IBD ) > & err &

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