# fullgo_paint_update
Update of Panther and PAINT DBs with monthly GO release data

## Updating GO tables
As this is being developed, the Makefile recipes will likely be called independent of each other. To execute the current existing workflow:
```
make download_fullgo
make extractfromgoobo
make extractfromgoobo_relation
make write_fullGoMappingPthr_slurm
```
Note: you'll also need a config/config.yaml file for the postgres DB caller (check `config.yaml.example`). Also, logging is not built in to the Makefile yet so you'll need to redirect output to a file. I like to do the following:
```
make do_stuff | tee -a log.txt
```
This will append to a file while still displaying to STDOUT.

* `download_fullgo` will download all current GAF and GO.obo files from GO ftp server. This also creates the base folder ("YYYY-MM-DD_fullgo/") where the update files will live.
* `extractfromgoobo` and `extractfromgoobo_relation` parse out the ontology terms and term relationships, respectively.
* `write_fullGoMappingPthr_slurm` is a convenience thing that creates a slurm batch script to run `scripts/fullGoMappingPthr.pl` on the USC HPC. This script maps the GAF gene product IDs to Panther IDs.

Once the input files `inputforGOClassification.tsv`, `goparentchild.tsv`, and `Pthr_GO.tsv` are generated, they're SCP'd over to the Panther DB server to be copied into staging tables. The following commands will then load the data into Panther and update the aggregation table:
```
make load_raw_go_to_panther
make update_panther_new_tables
make switch_panther_table_names
```

After these are run the Panther web server needs to be restarted before the changes are visible.

## Updating PAINT tables

```
make update_paint_go_classification
make update_paint_go_annotation
make update_paint_go_evidence
make update_paint_go_annot_qualifier
make switch_evidence_to_pmid
make delete_incorrect_go_annot_qualifiers
make update_paint_paint_annotation
make update_paint_paint_evidence
make update_comments_status
make run_restore_annots
make switch_paint_table_names
make regenerate_go_aggregate_view
```

## GAF generation
After update of both Panther and the PAINT curation DBs, queries are run against the curation DB to generate inputs for creating PAINT GAFs.
```
make paint_annotation
make paint_annotation_qualifier
make paint_evidence
make go_aggregate
make organism_taxon
make create_gafs
make repair_gaf_symbols
```
* `paint_annotation`, `paint_annotation_qualifier`, `paint_evidence`, `go_aggregate`, and `organism_taxon` generate the input files for `scripts/createGAF.pl`.
* `create_gafs` runs `scripts/createGAF.pl` to generate PAINT GAFs under the IBA_GAFs folder.
* `repair_gaf_symbols` is only used right now (at least until the next Reference Proteome release) to correct gene symbols in the PomBase PAINT GAF.
