# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated monthly pipeline for updating PANTHER and PAINT PostgreSQL databases with Gene Ontology (GO) release data. Downloads GO GAF files and ontology, maps gene products to PANTHER family IDs, loads into databases, and generates PAINT GAF output files.

## Key Commands

### Running Tests
```bash
python test.py                # Unit tests (tree parsing, node loading)
pytest tests/                 # Integration tests (requires DB + pthr_db_caller)
pytest tests/test_gaferencer.py  # Single test file
```

### Pipeline Execution
All pipeline steps are Makefile recipes, run individually and sequentially. Logging is manual:
```bash
make <recipe> | tee -a log.txt
```

**Panther pipeline:** `download_fullgo` → `extractfromgoobo` → `split_fullGoMappingPthr_gafs` → `slurm_fullGoMappingPthr` → `load_raw_go_to_panther` → `update_panther_new_tables` → `switch_panther_table_names`

**PAINT pipeline:** `load_raw_go_to_paint` → `update_paint_go_classification` → `update_paint_go_annotation` → `update_paint_go_evidence` → `update_paint_go_annot_qualifier` → `switch_evidence_to_pmid` → `delete_incorrect_go_annot_qualifiers` → `setup_preupdate_data` → `gen_iba_gaf_yamls` → `switch_table_names_go_only`

**GAF generation:** `paint_annotation` → `paint_annotation_qualifier` → `paint_evidence` → `go_aggregate` → `organism_taxon` → `create_gafs` → `repair_gaf_symbols`

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
