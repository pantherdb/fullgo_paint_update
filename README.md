# fullgo_paint_update
Update of Panther and PAINT DBs with monthly GO release data.
[Summary Google doc](https://docs.google.com/document/d/1Tx3DGLanQ1P6vBL6FWH5V5M7nVqCCCsqu-6m61jPtQ4/edit?usp=sharing)

## Updating GO tables
Logging is not built in to the Makefile yet so you'll need to redirect output to a file. I like to do the following:
```
make do_stuff | tee -a log.txt
```
This will append to a file while still displaying to STDOUT. You'll also need a config/config.yaml file for the postgres DB caller (check `config.yaml.example`). As this is being developed, the Makefile recipes will likely be called independent of each other. 

To execute the current existing workflow:
```
make download_fullgo
make extractfromgoobo
make split_fullGoMappingPthr_gafs
make slurm_fullGoMappingPthr
make BEFORE_DATE=<previous release date> compare_pthr_go_counts
make build_pthr_go_match
make SRC_HOST=<cluster> SRC_BASE_PATH=<remote BASE_PATH> fetch_release_files   # on your local machine
make DB_HOST=<db server> push_db_load_files
``` 

* `download_fullgo` will download all current GAF and GO.obo files from GO ftp server. This also creates the base folder ("YYYY-MM-DD_fullgo/") where the update files will live. Only the `*-uniprot.gaf.gz` species GAFs are downloaded by default; run `PREFER_MOD_GAFS=1 make download_fullgo` to take a species' `*-mod.gaf.gz` instead wherever one exists (useful when a `-uniprot` file drops annotations vs its `-mod` counterpart). Either way, `resources/gaf_source_by_proteome.tsv` overrides the choice per proteome — needed because PANTHER can't map every MOD ID namespace, so e.g. ECOLI (EcoCyc), XENLA (Xenbase) and SCHJY (JaponicusDB) must stay on `-uniprot` while DANRE (ZFIN) is better off on `-mod`. Check any edit to that file with `make compare_pthr_go_counts`.
* `extractfromgoobo` and `extractfromgoobo_relation` parse out the ontology terms and term relationships, respectively.
* `submit_fullGoMappingPthrHierarchy_slurm` will create a slurm batch script to run `scripts/fullGoMappingPthrHierarchy.pl` on the USC HPC and then submit it. This script maps the GAF gene product IDs to Panther IDs. It now also outputs files used for tracking ontology hierarchy.
* `fetch_release_files` and `push_db_load_files` move the release between machines. HPC can't reach the DB server through the firewall, so your local machine relays: the first pulls everything the local phases need out of the cluster's BASE_PATH, the second sends just the DB loading files on to the DB server's `load_dir`. The file list lives in `scripts/transfer_release_files.py` so you don't have to remember it, and both take `DRY_RUN=1` to show the transfers without doing them. After the GAFs are built, `push_gafs_to_ftp` and `archive_gafs_to_hpc` ship the `release_tarball` out to the file server and to HPC.
* `compare_pthr_go_counts` is a QA gate to run before loading into the DB. It reports per-proteome annotation and mapped-gene-product counts in `Pthr_GO_<version>.tsv` against the previous release, sorted by greatest percent deviation, and exits non-zero when a proteome moves by 10% or more (`PTHR_GO_DIFF_THRESHOLD`). This catches a GAF source or ID mapping change that guts a proteome — e.g. ECOLI going from a UniProt-centric GAF to a MOD-centric EcoCyc one dropped 54,316 annotations to 677.

Once the input files `inputforGOClassification.tsv`, `goparentchild.tsv`, and `Pthr_GO.tsv` are generated, `make push_db_load_files` sends them to the Panther DB server to be copied into staging tables. The following commands will then load the data into Panther and update the aggregation table:
```
make load_raw_go_to_panther
make update_panther_new_tables
make switch_panther_table_names
```

After these are run the Panther web server needs to be restarted before the changes are visible.

## Updating PAINT tables

```
make update_paint_tables
```
This runs the whole block in order. The step list lives in `scripts/run_paint_table_update.py`
(`make list_paint_table_steps` prints it) rather than here, so a step cannot be dropped by
retyping the block; a dropped step is otherwise not noticed until GAF generation produces
wrong output hours later.

Between the write-heavy steps it runs `scripts/settle_db_tables.py`, which waits for
autovacuum to drain off the tables that step just rewrote and then `VACUUM (ANALYZE)`s them.
`db_caller.py` commits each `.sql` file as one transaction, so autovacuum fires the instant a
step returns and the next step pays for it in a lock wait, in disk I/O, or in a plan built on
stats nothing has refreshed yet — worst case the freshly `CREATE`d `go_classification_descendants`
and `goanno_w_qualifier` matviews, which carry no stats at all until analyzed. The vacuum costs
the same either way; settling just makes it synchronous and visible instead of a surprise stall.

`switch_table_names_go_only` is the point of no return — it renames the `_new` tables over the
live ones. Everything before it only touches `_new` tables and can be re-run, so the switch is
gated: it prints `paint_go_table_counts` and asks first, and a run with no terminal to ask on
stops in front of it rather than flipping the live tables unattended.

| | |
|---|---|
| `make DRY_RUN=1 update_paint_tables` | print the plan, run nothing |
| `make CONFIRM_SWITCH=1 update_paint_tables` | unattended, switch included |
| `make START_AT=<step> update_paint_tables` | resume after a failure |
| `make STOP_AFTER=<step> update_paint_tables` | stop early (e.g. before the switch) |
| `make list_paint_table_steps` | print the step names |

On failure it stops at once and prints the failed step, the `AFFECTED_TABLES` list for
`scripts/util/reset_paint_table.sh`, and the exact `START_AT=` command to resume with. If a
*settle* fails the resume points at the following step: the step itself already committed, and
re-running it would hit an `ALTER TABLE ..._old RENAME TO ..._new` with no `_old` table left.

To settle tables by hand when a step is already stalling behind autovacuum:
```
make TABLES="go_annotation_new go_evidence_new" settle_db_tables
```

## GAF generation
After update of both Panther and the PAINT curation DBs, queries are run against the curation DB to generate inputs for creating PAINT GAFs.
```
make create_gafs
make create_gafs_goa
```
* `paint_annotation`, `paint_annotation_qualifier`, `paint_evidence`, `go_aggregate`, and `organism_taxon` generate the input files for `scripts/createGAF.pl`.
* `create_gafs` runs `scripts/createGAF.pl` to generate PAINT GAFs under the IBA_GAFs folder.
* `repair_gaf_symbols` is only used right now (at least until the next Reference Proteome release) to correct gene symbols in the PomBase PAINT GAF.

## FTP Tarball
```
make release_tarball
make FTP_HOST=<file server> FTP_PATH=<.../downloads/paint/19.0/YYYY-MM-DD> push_gafs_to_ftp
make HPC_HOST=<cluster> HPC_ARCHIVE_PATH=<archive dir> archive_gafs_to_hpc
```
* `release_tarball` packages `IBD.gaf`, the TreeGrafter annotations, `gene_association.paint_uniprot.gaf` and `presubmission/*.gaf.gz`.
* `push_gafs_to_ftp` sends that tarball to the file server and unpacks it into `FTP_PATH`, which should be the dated release dir itself. `archive_gafs_to_hpc` sends the same tarball to the cluster and leaves it packed. Both take `DRY_RUN=1`, and `RELEASE_TARBALL=` overrides the default (today's date) to push an older release.

## Updating PAN-GO tables and genelist_agg fields
If necessary, you can reuse this command to load from raw annot and ontology files into `goanno_wf`, `goobo_extract`, and `goobo_parent_child`:
```
make load_raw_go_to_panther
```
Then run these, making sure to replace the correct `PANGO_VERSION` and `PANGO_VERSION_DATE` values:
```
PANGO_VERSION=2.0.2 PANGO_VERSION_DATE=2024-12-05 make update_pango_new_tables
make switch_pango_table_names
```
