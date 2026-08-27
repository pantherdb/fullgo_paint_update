# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated monthly pipeline for updating PANTHER and PAINT PostgreSQL databases with Gene Ontology (GO) release data. Downloads GO GAF files and ontology, maps gene products to PANTHER family IDs, loads into databases, and generates PAINT GAF output files.

## Key Commands

### Running Tests
```bash
python test.py                # Unit tests (tree parsing, node loading)
pytest test_propagate_paint_ibas.py  # IBA propagation tests
pytest tests/                 # Integration tests (requires DB + pthr_db_caller)
pytest tests/test_gaferencer.py  # Single test file
```

### Pipeline Execution
All pipeline steps are Makefile recipes, run individually and sequentially. Logging is manual:
```bash
make <recipe> | tee -a log.txt
```

**Panther pipeline:** `download_fullgo` → `extractfromgoobo` → `split_fullGoMappingPthr_gafs` → `slurm_fullGoMappingPthr` → `compare_pthr_go_counts` → `fetch_release_files` → `push_db_load_files` → `load_raw_go_to_panther` → `update_panther_new_tables` → `switch_panther_table_names`

**Cross-machine transfers:** the pipeline spans HPC (phase 1), the local workstation (phases 2-3) and the DB server, and a firewall blocks HPC from reaching the DB server, so local relays. `scripts/transfer_release_files.py` owns the manifest of what has to move and why, so the list is not something to remember:
- `make SRC_HOST=<hpc> SRC_BASE_PATH=<remote BASE_PATH> fetch_release_files` — pulls the 9 files the local phases need: the 4 DB-load files plus `profile.txt`, `go.json`, `goparentchild_isaonly.tsv`, `resources/complex_terms.tsv` and `go.obo`. Each manifest entry records its consumer, and a missing one fails the recipe rather than surfacing hours later as a failed `COPY`.
- `make DB_HOST=<db> push_db_load_files` — sends only the 4 files a `{load_dir}` COPY reads (`Pthr_GO_$(PANTHER_VERSION).tsv`, `Pthr_GO_$(PANTHER_VERSION)_filtered.tsv`, `inputforGOClassification.tsv`, `goparentchild.tsv`) to `DB_LOAD_DIR`.
- `make FTP_HOST=<fs> FTP_PATH=<dated release dir> push_gafs_to_ftp` — ships the `release_tarball` payload and unpacks it remotely (`--strip-components=1`), so `FTP_PATH` should be the dated dir itself, e.g. `.../downloads/paint/19.0/2026-08-18`.
- `make HPC_HOST=<hpc> HPC_ARCHIVE_PATH=<dir> archive_gafs_to_hpc` — same tarball, left packed, for archival.

Transfers use rsync over ssh so an interrupted multi-GB file resumes. A compressed sibling is preferred on the wire where one exists (the filtered Pthr_GO is 235MB vs 1.9GB), searched as `.gz`, then `.tar.gz`, then the plain file — all three forms occur, since completed releases archive Pthr_GO as `.tsv.tar.gz`. Because `COPY` reads the plain `.tsv`, `push_db_load_files` expands whatever arrived on the DB server: `gunzip -f` for a `.gz`, `tar -xzOf … > <plain .tsv>` for a `.tar.gz`. Note a `.tsv.tar.gz` name also ends in `.gz`, so the two cases must not be conflated — `gunzip` on a tarball leaves an unreadable `.tsv.tar`. **Every recipe takes `DRY_RUN=1`** to print each transfer without moving anything — worth running first, these move multiple GB.

**GAF source selection:** `download_fullgo` takes one GAF per species from the release listing. The global default is every `*-uniprot.gaf.gz` (the long-term pipeline goal); `PREFER_MOD_GAFS=1` switches the default to `*-mod.gaf.gz` wherever one exists. `resources/gaf_source_by_proteome.tsv` (`GAF_SOURCE_BY_PROTEOME`) overrides that per proteome in either direction, so it reads as an always-mod list under the default and a never-mod list under the flag. It exists because PANTHER cannot map every MOD ID namespace back to UniProt — ECOLI (EcoCyc), XENLA (Xenbase) and SCHJY (JaponicusDB) lost 98.8%, 40.7% and 100% of their `Pthr_GO` annotations when switched to `-mod`, while DANRE (ZFIN) gained 44.7%. Breakage is per-proteome, not per-namespace: XENTR is also Xenbase and came through fine. An explicit `mod` with no `-mod` file falls back to `-uniprot`; an explicit `uniprot` with no `-uniprot` file skips the proteome rather than fall back to the banned source. Always confirm an edit with `compare_pthr_go_counts`.

**QA gate:** `make BEFORE_DATE=<prev release date> compare_pthr_go_counts` runs `scripts/compare_pthr_go_counts.py` to diff per-proteome annotation and mapped-gene-product counts in `Pthr_GO_$(PANTHER_VERSION).tsv` against the previous release, sorted by greatest percent deviation. It exists to catch a GAF-source or ID-mapping change that guts a proteome (e.g. ECOLI switched from a UniProt-centric GAF to a MOD-centric EcoCyc one: 54,316 annotations → 677). Exits non-zero on any proteome deviating by `PTHR_GO_DIFF_THRESHOLD` percent (default 10.0), so it fails the recipe before the DB load; pass `--no_fail` to run it advisory-only. Reads the previous release's Pthr_GO whether it is a plain `.tsv`, `.tsv.gz`, or archived `.tsv.tar.gz`. Writes `$(BASE_PATH)/pthr_go_count_diff.tsv`.

**PAINT pipeline:** `load_raw_go_to_paint` → `update_paint_go_classification` → `update_paint_go_annotation` → `update_paint_go_evidence` → `update_paint_go_annot_qualifier` → `switch_evidence_to_pmid` → `delete_incorrect_go_annot_qualifiers` → `setup_preupdate_data` → `gen_iba_gaf_yamls` → `switch_table_names_go_only`

**PAINT pipeline, one command:** `make update_paint_tables` runs that whole block via
`scripts/run_paint_table_update.py`, which owns the step list (`make list_paint_table_steps`).
Between write-heavy steps it runs `scripts/settle_db_tables.py`: `db_caller.py` executes a whole
`.sql` file on one non-autocommit connection and commits at the end, so autovacuum fires the
instant a step returns and stalls the next one on its lock, its I/O, or stats it has not
refreshed — acutely for `go_classification_descendants` and `goanno_w_qualifier`, matviews the
pipeline `DROP`s and `CREATE`s, which carry no stats until analyzed. Settling waits the vacuum
out and then `VACUUM (ANALYZE)`s explicitly, which also resets the dead-tuple counters so
autovacuum has no reason to re-fire mid-step. This cannot be a `.sql` file through `db_caller.py`
— `VACUUM` cannot run in a transaction block and `DBCaller` never sets autocommit, so the script
opens its own autocommit connection off `DBCallerConfig`.

`switch_table_names_go_only` is the point of no return; everything before it only touches `_new`
tables. It is gated — prints `paint_go_table_counts`, asks, and stops in front of the switch when
there is no terminal to ask on. `CONFIRM_SWITCH=1` proceeds unattended, `DRY_RUN=1` prints the
plan, `START_AT=`/`STOP_AFTER=` bound the range. A preflight checks `config/config.yaml`,
`profile.txt` and `resources/complex_terms.tsv` up front so a missing file costs seconds, not
hours. On failure it prints the failed step, `AFFECTED_TABLES` for
`scripts/util/reset_paint_table.sh`, and the `START_AT=` resume command — pointing at the
*following* step when a settle failed, since the step itself already committed and its
`ALTER TABLE ..._old RENAME` cannot run twice. `scripts/run_paint_pipeline.sh` is the superseded
predecessor: stale step list, hardcoded `_fullgo_test` BASE_PATH, and no `set -o pipefail` behind
its `| tee`, so it never saw a non-zero exit code.

**GAF generation:** `paint_annotation` → `paint_annotation_qualifier` → `paint_evidence` → `go_aggregate` → `organism_taxon` → `create_gafs` → `repair_gaf_symbols` → `propagate_paint_ibas` → `release_tarball` → `push_gafs_to_ftp` / `archive_gafs_to_hpc`

**IBA propagation:** `make propagate_paint_ibas` runs `scripts/propagate_paint_ibas.py` to propagate PAINT IBD GO annotations down PANTHER trees, producing `$(BASE_PATH)/PAINT_TreeGrafter_Annotations_TOTAL.txt` for the TreeGrafter pipeline. Reads the IBD GAF emitted by `create_gafs` (`$(BASE_PATH)/IBD`), the per-version NHX trees (`TREEGRAFTER_TREE_DIR`), `annotation_treegrafter.dat` (`TREEGRAFTER_ANNOTATION_PATH`, SF/PC only), and `node.dat` (`NODE_PATH`). Set `TREEGRAFTER_TREE_DIR` and `TREEGRAFTER_ANNOTATION_PATH` in `config.mk` for the active PANTHER version. Uses `pthr_db_caller.haiming_to_newick` for NHX→Newick conversion. Design doc: `.plans/2026-03-05-propagate-paint-ibas-design.md`. Implementation plan: `.plans/2026-03-05-propagate-paint-ibas.md`.

**PAN-GO update:**
```bash
make load_raw_go_to_panther
PANGO_VERSION=2.0.2 PANGO_VERSION_DATE=2024-12-05 make update_pango_new_tables
make switch_pango_table_names
```

### Dependencies
```bash
pip install -r requirements.txt
```

## Architecture

See `docs/` for detailed documentation:
- `docs/architecture.md` — component map, language mix, database design, external dependencies
- `docs/data-pipeline.md` — all pipeline phases, data flow, SQL deep dives
- `docs/configuration.md` — all config sources, variable relationships, real-world examples
- `docs/orchestration.md` — execution model, SLURM integration, cross-machine topology, error handling
- `docs/testing.md` — current coverage, untested components, suggested improvements

### Quick Reference

- **Current version**: PANTHER 19.0, `CLS_VER_ID = 31`
- **Config files**: `config.mk` (Makefile paths, not in repo), `config/config.yaml` (DB credentials, see `config.yaml.example`), `profile.txt` (auto-generated version metadata)
- **Key variables**: `BASE_PATH` (working dir), `PANTHER_VERSION` (library paths + CLS_VER_ID), `GAF_VERSION` (default 2.2)
- **Scripts**: Perl (`scripts/*.pl`) for data processing, Python (`scripts/*.py`) for downloads/DB/reporting, SQL (`scripts/sql/`) for DB mutations, SLURM (`scripts/*.slurm`) for HPC jobs
- **Databases**: `panther` schema (public) and `panther_upl` schema (PAINT curation). Updates use staging tables with atomic rename swap.
- **Key dependency**: `pthr_db_caller` (v2.0.2, PyPI: `pip install pthr-db-caller`) — DB connections, tree graphs, taxon validation
- **Resources**: `resources/` — static data files (taxon lists, ID mappings, IBA configs, test fixtures)
