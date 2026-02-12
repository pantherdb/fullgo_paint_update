# Architecture

## System Purpose

This pipeline automates the monthly update of two PostgreSQL databases -- PANTHER (public gene classification) and PAINT/Curation (phylogenetic annotation) -- with new Gene Ontology (GO) release data. It downloads GO annotation files, maps gene products to PANTHER protein families, loads the data into staging tables, and generates per-organism IBA (Inferred from Biological Ancestry) GAF files for distribution.

## Component Map

```
                          GO Consortium / GOEx FTP
                                  |
                                  v
                    +----------------------------+
                    |    Download Layer           |
                    |    (download_goex.py)       |
                    +----------------------------+
                                  |
                                  v
                    +----------------------------+
                    |    Ontology Parsing         |
                    |    (extractfromgoobo*.pl,   |
                    |     FindAllParents.pl,      |
                    |     printHierarchy.pl)      |
                    +----------------------------+
                                  |
                                  v
                    +----------------------------+
                    |    Gene-to-PANTHER Mapping  |
                    |    (fullGoMappingPthr-      |
                    |     Hierarchy.pl via SLURM) |
                    +----------------------------+
                                  |
                                  v
                    +----------------------------+
                    |    Database Loading         |
                    |    (SQL via db_caller.py)   |
                    +------|------------|--------+
                           |            |
                    +------v---+  +-----v--------+
                    | panther  |  | panther_upl   |
                    | schema   |  | schema        |
                    | (public) |  | (curation)    |
                    +------+---+  +-----+---------+
                           |            |
                           v            v
                    +----------------------------+
                    |    GAF Generation           |
                    |    (createGAF.pl)           |
                    +----------------------------+
                                  |
                                  v
                    +----------------------------+
                    |    Reporting / QC           |
                    |    (iba_count.py,           |
                    |     compare_paint_releases) |
                    +----------------------------+
```

## Language Mix

The codebase is polyglot, reflecting its evolution over time:

| Language | Purpose | Files |
|----------|---------|-------|
| **Perl** | Core data processing: GAF parsing/generation, ontology extraction, gene-to-PANTHER mapping. These are the computationally intensive, performance-critical scripts. | ~10 `.pl` files |
| **Python** | Orchestration glue: downloads, DB interaction, reporting, comparison tools. Newer scripts are all Python. | ~15 `.py` files |
| **SQL** | All database mutations: staging table loads, update logic, table swaps. SQL files use shell variable substitution (`{variable}` placeholders). | ~40 `.sql` files |
| **Make** | Pipeline orchestration: recipe ordering, variable management, SLURM job submission. | 1 `Makefile` (31KB) |
| **Bash/CSH** | SLURM job templates, shell wrappers for createGAF.pl | ~16 `.slurm`, ~5 `.sh` files |

## Key Data Formats

- **GAF (Gene Association Format) 2.2**: Tab-delimited gene-to-GO term associations. The primary input from GO and primary output for distribution.
- **OBO**: GO ontology definition format (go.obo). Parsed into TSV for DB loading.
- **node.dat / gene.dat / identifier.dat**: PANTHER library binary/text files mapping genes to protein family trees.
- **treeNodes/**: Per-family Newick-like phylogenetic tree files used by createGAF.pl to traverse ancestry.
- **GPI (Gene Product Information)**: Cross-reference files from UniProt, ZFIN, JaponicusDB for gene ID resolution.

## Database Architecture

### Two-Database Design

1. **`panther` schema** (public PANTHER database)
   - Stores GO classification hierarchy, fullgo version metadata, and per-gene GO annotation aggregates
   - Used by the public PANTHER web interface
   - Tables: `go_classification`, `go_classification_relationship`, `fullgo_version`, `genelist_agg`

2. **`panther_upl` schema** (PAINT curation database, called "Curation")
   - Stores the full GO annotation model: `go_annotation`, `go_evidence`, qualifiers
   - Stores PAINT curator annotations: `paint_annotation`, `paint_evidence`, curation status, comments
   - Contains precomputed lookup tables: `node_all_ancestors`, `node_all_leaves`, `go_classification_descendants`
   - Materialized views: `go_aggregate`, `paint_exp_aggregate`
   - This schema is considerably more complex, with ~13 tables affected by the update pipeline

### Staging Pattern

All table updates use a staging/swap pattern:
1. Copy current table to `_new` suffix
2. Perform all mutations on `_new` tables
3. Atomically rename: current -> `_old`, `_new` -> current
4. Drop `_old` tables (or keep as backup)

This provides zero-downtime updates and rollback capability via `reset_table_names.sql`.

## External Dependencies

### Critical: `pthr_db_caller` (v2.0.2)

This is a first-party Python package that provides:
- `DBCaller`: PostgreSQL connection management and SQL execution with YAML-based config
- `PantherTreeGraph`: NetworkX-based phylogenetic tree traversal
- `TaxonTermValidator`: Taxon constraint validation
- `mod_id_mapper`: Model organism database ID resolution
- Data models for PANTHER entities

The package is PyPI-hosted (`pip install pthr-db-caller`) and is the single most critical dependency. It encapsulates all database connection logic and is used by both the pipeline scripts and the test suite.

### Infrastructure

- **USC HPC Cluster**: SLURM scheduler for compute-intensive Perl jobs (gene mapping, GAF generation)
- **PostgreSQL**: Two database instances (PANTHER public, PAINT curation)
- **Google Sheets API**: Automated publishing of QC reports
- **NCBI PubMed FTP**: Linkout file uploads
- **ROBOT tool**: OWL ontology processing for complex terms and GO aspects

### Python packages
- `psycopg2` -- PostgreSQL adapter
- `PyYAML` -- config parsing
- `biopython` -- NHX phylogenetic tree parsing
- `oaklib` -- OBO Foundry ontology access (used in paint_exp_to_gaf.py)
- `SPARQLWrapper`, `prefixcommons` -- SPARQL queries for taxon name resolution
- `requests`, `bs4`, `tqdm` -- HTTP downloads
- `google-api-python-client` -- Sheets publishing

## File Organization

```
fullgo_paint_update/
  Makefile                    # Pipeline orchestrator (31KB)
  config.yaml.example        # DB credential template
  profile.txt                # Version metadata template
  requirements.txt           # Python dependencies
  test.py                    # Unit tests
  resources/                 # Static data files
    organism.dat              #   Organism-to-taxon mappings
    paint_taxons*.txt          #   Version-specific taxon lists
    uniprot_to_araport_map_gaf.tsv  # Arabidopsis ID mapping
    iba_gaf_gen_*.yaml        #   Before/after comparison templates
    test/                     #   Test fixtures
  scripts/
    *.py                      # Python scripts (download, DB ops, reporting)
    *.pl                      # Perl scripts (data processing, GAF generation)
    *.sh                      # Shell wrappers
    *.slurm                   # SLURM job templates
    sql/
      panther_go_update/      #   PANTHER pipeline SQL
      paint_go_update/        #   PAINT pipeline SQL (most complex)
      fix/                    #   One-off correction scripts
      reports/                #   Reporting queries
      test/                   #   Test/verification queries
    util/
      pthr_data.py            # Model organism taxon ID list
      publish_google_sheet.py # Google Sheets API wrapper
  tests/
    test_gaferencer.py        # Integration test (requires DB)
```

## Discussion Points

### Mixed Language Concern
The Perl/Python split is a maintenance burden. The Perl scripts (especially `createGAF.pl` at ~40KB) are the most complex and least maintainable parts of the system. They handle critical business logic (tree traversal, redundancy filtering, qualifier validation) that is difficult to test in isolation. A gradual migration to Python would improve testability and onboarding, but the Perl scripts are battle-tested and performant.

### `pthr_db_caller` as Hidden Architecture
Significant architectural decisions are encapsulated in the `pthr_db_caller` package (v2.0.2), hosted on PyPI (`pip install pthr-db-caller`). Its SQL execution model, config parsing, and tree graph implementation are core to the system but invisible from this codebase. The pinned version (==2.0.2) provides stability, but changes to `pthr_db_caller` can silently break this pipeline if the pin is bumped without testing.

### Hardcoded HPC Paths
All PANTHER library paths (`/auto/rcf-proj3/...`, `/project/huaiyumi_14/...`) are hardcoded in the Makefile's `ifeq` blocks. These are USC Discovery cluster paths that won't exist on other systems. The `config.mk` include provides some abstraction, but the core path logic is baked into the Makefile.

### No Schema Definition Files
The database schema is implied by the SQL scripts but never explicitly defined in this repo. There are no migration files, no CREATE TABLE statements (except for raw staging tables), and no ERD. Understanding the schema requires reading the SQL update scripts or inspecting the live database.

### Monolithic createGAF.pl
At ~40KB with ~1000 lines of procedural Perl, `createGAF.pl` is the system's most complex component. It parses 10+ input files, implements tree traversal, redundancy filtering, and GAF formatting all in a single script. Three variants exist (`createGAF.pl`, `createGAF_human_exp_references.pl`, `createGAFallDescendants.pl`) with significant code duplication.
