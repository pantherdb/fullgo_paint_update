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

**Panther pipeline:** `download_fullgo` → `extractfromgoobo` → `split_fullGoMappingPthr_gafs` → `slurm_fullGoMappingPthr` → `compare_pthr_go_counts` → `load_raw_go_to_panther` → `update_panther_new_tables` → `switch_panther_table_names`

**GAF source selection:** `download_fullgo` takes one GAF per species from the release listing. The global default is every `*-uniprot.gaf.gz` (the long-term pipeline goal); `PREFER_MOD_GAFS=1` switches the default to `*-mod.gaf.gz` wherever one exists. `resources/gaf_source_by_proteome.tsv` (`GAF_SOURCE_BY_PROTEOME`) overrides that per proteome in either direction, so it reads as an always-mod list under the default and a never-mod list under the flag. It exists because PANTHER cannot map every MOD ID namespace back to UniProt — ECOLI (EcoCyc), XENLA (Xenbase) and SCHJY (JaponicusDB) lost 98.8%, 40.7% and 100% of their `Pthr_GO` annotations when switched to `-mod`, while DANRE (ZFIN) gained 44.7%. Breakage is per-proteome, not per-namespace: XENTR is also Xenbase and came through fine. An explicit `mod` with no `-mod` file falls back to `-uniprot`; an explicit `uniprot` with no `-uniprot` file skips the proteome rather than fall back to the banned source. Always confirm an edit with `compare_pthr_go_counts`.

**QA gate:** `make BEFORE_DATE=<prev release date> compare_pthr_go_counts` runs `scripts/compare_pthr_go_counts.py` to diff per-proteome annotation and mapped-gene-product counts in `Pthr_GO_$(PANTHER_VERSION).tsv` against the previous release, sorted by greatest percent deviation. It exists to catch a GAF-source or ID-mapping change that guts a proteome (e.g. ECOLI switched from a UniProt-centric GAF to a MOD-centric EcoCyc one: 54,316 annotations → 677). Exits non-zero on any proteome deviating by `PTHR_GO_DIFF_THRESHOLD` percent (default 10.0), so it fails the recipe before the DB load; pass `--no_fail` to run it advisory-only. Reads the previous release's Pthr_GO whether it is a plain `.tsv`, `.tsv.gz`, or archived `.tsv.tar.gz`. Writes `$(BASE_PATH)/pthr_go_count_diff.tsv`.

**PAINT pipeline:** `load_raw_go_to_paint` → `update_paint_go_classification` → `update_paint_go_annotation` → `update_paint_go_evidence` → `update_paint_go_annot_qualifier` → `switch_evidence_to_pmid` → `delete_incorrect_go_annot_qualifiers` → `setup_preupdate_data` → `gen_iba_gaf_yamls` → `switch_table_names_go_only`

**GAF generation:** `paint_annotation` → `paint_annotation_qualifier` → `paint_evidence` → `go_aggregate` → `organism_taxon` → `create_gafs` → `repair_gaf_symbols` → `propagate_paint_ibas`

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
