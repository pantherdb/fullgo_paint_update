# Orchestration

## Execution Model

The pipeline is orchestrated by a 537-line Makefile containing ~50 recipes. Each recipe is a self-contained step that must be invoked manually and sequentially. There is no automated end-to-end execution for the full pipeline, though `scripts/run_paint_pipeline.sh` automates the PAINT portion.

### Manual Sequential Execution

The standard operating procedure is:
```bash
make download_fullgo | tee -a log.txt
make extractfromgoobo | tee -a log.txt
make split_fullGoMappingPthr_gafs | tee -a log.txt
make slurm_fullGoMappingPthr | tee -a log.txt
# ... wait for SLURM jobs to complete ...
make load_raw_go_to_panther | tee -a log.txt
# ... and so on
```

Each step produces console output. Logging is the operator's responsibility (via `tee`). The operator must verify each step's output before proceeding to the next.

### Why Not Fully Automated?

Several factors prevent full automation:
1. **SLURM job submission**: Some steps submit HPC jobs and return immediately. The operator must wait for completion before proceeding.
2. **Manual verification**: Several steps produce counts or diffs that should be reviewed.
3. **Duration**: The full pipeline takes many hours. Steps like `update_paint_go_annotation` run ~1 hour.
4. **Failure recovery**: If a step fails, manual intervention is needed before re-running.
5. **Cross-machine execution**: Some steps run on HPC (SLURM), some on a local machine, some require DB server access.

## Makefile Structure

### Variable Hierarchy

```
config.mk (user overrides)
  |
  v
Makefile defaults (PANTHER_VERSION=15.0, GAF_VERSION=2.2, etc.)
  |
  v
ifeq blocks (version-specific paths based on PANTHER_VERSION)
  |
  v
Computed variables (BASE_PATH, GO_VERSION_DATE from profile.txt)
  |
  v
Exported to environment (for envsubst and child processes)
```

### Recipe Categories

**Pipeline steps** (must be run in order):
- `download_fullgo`, `extractfromgoobo`, `split_fullGoMappingPthr_gafs`, `slurm_fullGoMappingPthr`
- `load_raw_go_to_panther`, `update_panther_new_tables`, `switch_panther_table_names`
- `load_raw_go_to_paint`, `update_paint_go_classification`, `update_paint_go_annotation`, etc.
- `paint_annotation`, `paint_evidence`, ..., `create_gafs`, `repair_gaf_symbols`

**Utility recipes** (run as needed):
- `raw_table_count`, `panther_table_count`, `paint_table_counts` -- verification
- `backup_paint_tables`, `refresh_paint_panther_upl` -- backup/restore
- `reset_paint_table_names` -- undo table swap
- `check_dups`, `regenerate_go_aggregate_view` -- maintenance

**Pattern rules** (file-based targets):
- `%/resources/complex_terms.tsv` -- ROBOT extraction
- `%/resources/panther_blacklist.txt` -- blacklist generation
- `%/TaxonConstraintsLookup.txt` -- taxon constraint table
- `%/gene_association.paint_exp.gaf` -- experimental GAF

## SLURM Integration

### Job Submission Pattern

```
Makefile recipe
  |
  +--> envsubst < scripts/template.slurm > $BASE_PATH/expanded.slurm
  +--> sbatch $BASE_PATH/expanded.slurm
         |
         +--> [runs on HPC compute node]
```

All SLURM templates live in `scripts/` and are expanded with `envsubst` before submission. The expanded versions are saved in `$BASE_PATH/` for debugging.

### SLURM Job Types

| Template | Purpose | Wait? |
|----------|---------|-------|
| `gunzip_gafs.slurm` | Decompress downloaded GAFs | No |
| `mkdir_fullGoMappingPthr_groups.slurm` | Split GAFs into groups | `--wait` |
| `fullGoMappingPthrHierarchy_para.slurm` | Parallel gene-to-PANTHER mapping | No |
| `robot_complex_terms.slurm` | Extract complex terms via ROBOT | `--wait` |
| `create_panther_gene_blacklist.slurm` | Build gene blacklist | `--wait` |
| `cut_uniprot_ids.slurm` | Extract UniProt IDs from GPI | `--wait` |
| `format_taxon_term_table.slurm` | Build taxon constraint table | No |
| `createGAF.slurm` | GAF generation (alternative to shell) | No |

**`--wait` flag**: Some `sbatch` calls use `--wait` to block the Makefile until the job completes. This is used for steps that must complete before the next recipe. Steps without `--wait` return immediately, requiring the operator to monitor job completion.

### Parallel Mapping Job

The gene-to-PANTHER mapping is the most compute-intensive step and uses SLURM array parallelism:

1. `mkdir_fullGoMappingPthr_groups.sh` splits GAF files into N groups of ~5GB
2. `fullGoMappingPthrHierarchy_para.slurm` submits an array job with N tasks
3. `fullGoMappingPthrHierarchy_para.csh` selects the group based on `SLURM_PROCID`
4. Each task runs `fullGoMappingPthrHierarchy.pl` on its group
5. Partial results are concatenated after all tasks complete

## `run_paint_pipeline.sh` (Semi-automated PAINT Pipeline)

This script automates the PAINT update portion by calling each Makefile recipe sequentially:

```bash
START_TIME=$SECONDS
BASE_PATH=$(date +%Y-%m-%d)_fullgo_test

make BASE_PATH=$BASE_PATH load_raw_go_to_paint | tee -a $BASE_PATH/log.txt
make BASE_PATH=$BASE_PATH update_paint_go_classification | tee -a $BASE_PATH/log.txt
AFFECTED_TABLES="go_classification go_classification_relationship fullgo_version"
make BASE_PATH=$BASE_PATH update_paint_go_annotation | tee -a $BASE_PATH/log.txt
# ... 12 more steps ...

echo $AFFECTED_TABLES
ELAPSED_TIME=$(($SECONDS - $START_TIME))
echo "Pipeline finished in $ELAPSED_TIME sec"
```

Key characteristics:
- Hardcodes `BASE_PATH` to `$(date +%Y-%m-%d)_fullgo_test` (test suffix)
- Tracks `AFFECTED_TABLES` for manual rollback reference
- No error checking between steps -- a failing step logs its error but the script continues
- Provides timing information
- Includes rollback instructions in comments

## Error Handling

### Current State: Minimal

- **No step-level error checking**: Makefile recipes don't use `set -e` or check return codes between commands within a recipe.
- **No pipeline-level error checking**: `run_paint_pipeline.sh` doesn't check exit codes between steps.
- **No retry logic**: Failed steps must be manually investigated and re-run.
- **No rollback automation**: `reset_paint_table.sh` exists but must be manually invoked with the correct table names.
- **No alerting**: No email, Slack, or other notification on failure.

### Recovery Procedures

**For PAINT pipeline failures**:
1. Note which tables were affected (tracked by `AFFECTED_TABLES` in `run_paint_pipeline.sh`)
2. Run `./scripts/util/reset_paint_table.sh {AFFECTED_TABLES}` to rename `_old` tables back
3. On DB server: run `./restore_paint_table.sh {AFFECTED_TABLES}` if restore from dump needed
4. Investigate and fix the issue
5. Re-run from the failed step

**For PANTHER pipeline failures**:
1. The `switch_panther_table_names` step is the critical point -- before it, the live tables are untouched
2. After the switch, `_old` tables serve as backup
3. Restoration requires manual SQL to reverse the rename

## Cross-Machine Coordination

The pipeline spans three machines with manual file transfers between them. A firewall restriction prevents HPC from connecting directly to the DB servers, so the operator's local machine acts as a relay.

### Execution Topology

```
USC HPC head node              Local workstation              DB server(s)
  |                                  |                            |
  | Phase 1: Data acquisition        |                            |
  |  make download_fullgo            |                            |
  |  make extractfromgoobo           |                            |
  |  make split/slurm (SLURM jobs)   |                            |
  |  -> Pthr_GO.tsv, *.tsv created   |                            |
  |                                  |                            |
  |--------- scp loading files ----->|                            |
  |                                  |-------- scp to load_dir -->|
  |                                  |                            |
  |                                  | Phase 2: DB update         |
  |                                  |  make load_raw_go_to_*     |
  |                                  |  make update_*             |
  |                                  |  make switch_*             |
  |                                  |                            |
  |                                  | Phase 3: GAF generation    |
  |                                  |  make create_gafs          |
  |                                  |  -> IBA_GAFs/ created      |
  |                                  |                            |
  |<-------- scp GAFs (backup) ------|                            |
  |                                  |-------- scp GAFs --------->| file server
```

### Phase-by-Machine Breakdown

**HPC head node** (phases 1):
- Download GO release files from GOEx FTP
- Parse ontology (`extractfromgoobo`)
- Map genes to PANTHER families (`fullGoMappingPthrHierarchy.pl` via SLURM)
- Previously required ~5 parallel SLURM procs when downloading from the GO release site; now GOEx files are smaller and only need 1 proc

**Local workstation** (phases 2-3):
- Receives loading files from HPC via SCP
- SCPs loading files to DB server's `load_dir` (e.g., `/pgres_data/data/`)
- Runs all DB update recipes (`load_raw_go_to_*`, `update_*`, `switch_*`)
- Runs GAF generation (`create_gafs`)
- Runs reporting (`run_reports`)

**DB server(s)**:
- Receives loading files in `load_dir` for PostgreSQL `COPY` commands
- Executes SQL via `pthr_db_caller` connections from local workstation

**File server** (post-pipeline):
- Receives final GAF files via SCP for public hosting

**HPC** (post-pipeline):
- Receives GAF files via SCP for archival/backup

### Manual File Transfers

The SCP transfers are manual and undocumented in the Makefile. The operator must:

1. After SLURM jobs complete on HPC:
   ```bash
   scp hpc:$BASE_PATH/Pthr_GO_*.tsv ./
   scp hpc:$BASE_PATH/inputforGOClassification.tsv ./
   scp hpc:$BASE_PATH/goparentchild*.tsv ./
   # ... other loading files
   ```

2. Before `load_raw_go_to_*`:
   ```bash
   scp Pthr_GO_*.tsv dbserver:/pgres_data/data/
   scp inputforGOClassification.tsv dbserver:/pgres_data/data/
   # ... etc
   ```

3. After `create_gafs`:
   ```bash
   scp -r IBA_GAFs/ fileserver:/path/to/hosting/
   scp -r IBA_GAFs/ hpc:/path/to/backup/
   ```

These transfers are a pain point: they are error-prone, undocumented, and break the pipeline into disconnected segments that can't be scripted end-to-end.

## Timing and Monitoring

### Known Durations (from comments and `run_paint_pipeline.sh`)

| Step | Approximate Duration |
|------|---------------------|
| `update_paint_go_annotation` | ~1 hour |
| `update_paint_go_evidence` | ~17 minutes |
| `update_paint_paint_evidence` | ~19 minutes |
| `obsolete_redundant_ibds` | ~14 minutes |
| `create_gafs` | Variable (depends on annotation count) |
| Full PAINT pipeline | Several hours |

### Monitoring

- Console output via `tee -a log.txt`
- `wc -l` commands after ontology parsing for quick sanity checks
- Table count recipes (`raw_table_count`, `panther_table_count`) for before/after verification
- SLURM job monitoring via `squeue`, `sacct`

## Discussion Points

### No Dependency Graph
The Makefile's pipeline recipes are all `.PHONY` targets with no declared prerequisites on each other. Make's dependency resolution is not used for ordering. This means:
- `make update_panther_new_tables` can be run without `load_raw_go_to_panther` having been run first
- There's no way to run `make full_pipeline` and have everything execute in order
- The ordering knowledge lives only in documentation and operator experience

### `run_paint_pipeline.sh` Doesn't Stop on Failure
The script chains `make` calls without `set -e` or exit code checking. If `update_paint_go_annotation` fails, `update_paint_go_evidence` will still run, likely corrupting data or producing confusing errors.

### SLURM Wait Inconsistency
Some `sbatch` calls use `--wait` (blocking) and some don't. The ones without `--wait` require the operator to manually check job completion before proceeding. This is error-prone.

### `envsubst` Security
Shell variable substitution via `envsubst` on SLURM templates has no escaping or validation. If any variable value contains shell metacharacters, the expanded script could behave unexpectedly.

### Firewall-Forced Relay Topology
The HPC cluster cannot connect to DB servers due to a firewall restriction. This forces the operator's local machine to act as a relay, requiring two SCP hops (HPC -> local -> DB server) for loading files and two more (local -> file server, local -> HPC) for output GAFs. This is the most significant operational pain point: it breaks the pipeline into disconnected segments, requires manual file tracking, and prevents end-to-end automation. Possible mitigations include a bastion/jump host, an rsync staging area, or a shared filesystem visible to both HPC and DB servers.

### No Dry-Run Capability
There is no way to preview what a pipeline step will do without actually doing it. This is particularly concerning for the SQL update steps that modify production databases.

### Logging Fragility
Logging depends on the operator piping each command through `tee`. If they forget, the output is lost. There is no built-in logging mechanism.
