# Data Pipeline

## Overview

The pipeline transforms Gene Ontology (GO) release data into PANTHER database updates and PAINT IBA GAF files. It runs monthly and consists of three major phases: data acquisition, database update, and GAF generation.

## Phase 1: Data Acquisition

### Step 1: Download GO Release (`download_fullgo`)

**Script**: `scripts/download_goex.py` (current) or `scripts/download_fullgo.py` (legacy)

**Source**: `https://ftp.ebi.ac.uk/pub/contrib/goa/goex/current/`

**Downloads**:
- All `.gaf.gz` files from `uniprot-centric/gaf/` subdirectory (species-specific GAFs)
- `release_date.txt` -- GO release version identifier
- `ontology/go.obo` -- GO ontology definitions
- `ontology/extensions/go-gaf.owl` -- GAF validation ontology
- `ontology/subsets/gocheck_do_not_annotate.owl` -- terms that should not be annotated

**Outputs** (to `$BASE_PATH/`):
- `gaf_files/*.gaf.gz` -> decompressed via SLURM `gunzip_gafs.slurm`
- `downloaded_files.txt` -- log of all downloaded URLs
- `release_date.txt` -- used by profile generation
- `go.obo` -- input for ontology parsing

**Post-download** (triggered by `download_fullgo` recipe):
- `make_profile` -- generates `profile.txt` (GO version date + PANTHER version)
- `make_readme` -- generates README with download metadata
- `complex_terms.tsv` -- ROBOT extraction of protein-containing complex descendants
- `panther_blacklist.txt` -- UniProt IDs not in PANTHER (from UniProt GPI)
- `TaxonConstraintsLookup.txt` -- taxon-term constraint table

### Step 2: Parse Ontology (`extractfromgoobo`)

**Scripts**: `extractfromgoobo.pl`, `extractfromgoobo_relation.pl`, `FindAllParents.pl`, `printHierarchy.pl`

**Data flow**:
```
go.obo
  |
  +--> extractfromgoobo.pl
  |      +--> inputforGOClassification.tsv   (GO terms with accession, name, aspect, definition)
  |      +--> obsolete_go_terms.txt          (alt_id mappings, obsoleted terms, replaced_by)
  |
  +--> extractfromgoobo_relation.pl
         +--> goparentchild.tsv              (all parent-child: is_a + part_of)
         +--> goparentchild_isaonly.tsv       (is_a only)
         |
         +--> FindAllParents.pl
                +--> AllParentsofGOTerms.txt  (transitive closure)
                |
                +--> printHierarchy.pl
                       +--> FinalChildParent-Hierarchy.dat  (formatted for mapping scripts)
```

**Key detail**: GO term type mapping is `biological_process` -> 12, `cellular_component` -> 13, `molecular_function` -> 14. These IDs match the `term_type_sid` column in the database.

### Step 3: Map Genes to PANTHER Families (`split_fullGoMappingPthr_gafs` + `slurm_fullGoMappingPthr`)

**Scripts**: `mkdir_fullGoMappingPthr_groups.sh`, `fullGoMappingPthrHierarchy.pl`

**Parallelization**: GAF files are split into groups of ~5GB each. The `goa_uniprot_all` file (which is very large) gets split at 300M lines. SLURM runs one process per group.

**Mapping strategy** (in order of precedence):
1. UniProt ID direct match against `identifier.dat`
2. Gene ID + database name match
3. Gene ID + taxon ID match
4. Alternate ID match
5. Gene symbol match

**Outputs**:
- `Pthr_GO_$VERSION.tsv` -- gene-to-GO mapping (tab-delimited: PANTHER_ID, GO_term, evidence_code, qualifier, with, reference, date, DB, gene_name, taxon)
- `GOWithHierarchy-{BP,MF,CC}-$VERSION.dat` -- hierarchy-expanded mappings per aspect

## Phase 2: Database Update

### PANTHER Pipeline (public database)

Operates on the `panther` schema.

| Step | Recipe | SQL File | Effect |
|------|--------|----------|--------|
| 1 | `load_raw_go_to_panther` | `panther_go_update/load_raw_go.sql` | Truncates and COPYs `Pthr_GO.tsv`, `inputforGOClassification.tsv`, `goparentchild.tsv` into staging tables (`goanno_wf`, `goobo_extract`, `goobo_parent_child`) |
| 2 | `update_panther_new_tables` | `go_classification.sql`, `fullgo_version.sql`, `genelist_agg.sql` | Builds `_new` tables: GO classification hierarchy, version metadata, per-gene aggregated GO annotations |
| 3 | `switch_panther_table_names` | `switch_table_names.sql` | Atomic rename: current -> `_old`, `_new` -> current |

### PAINT Pipeline (curation database)

Operates on the `panther_upl` schema. This is considerably more complex because it must preserve manually curated PAINT annotations while updating the underlying GO data.

| Step | Recipe | SQL File | Effect | Duration |
|------|--------|----------|--------|----------|
| 1 | `load_raw_go_to_paint` | `paint_go_update/load_raw_go.sql` | Loads same raw files into panther_upl staging tables | ~minutes |
| 2 | `update_paint_go_classification` | `go_classification.sql` | Updates GO terms: preserves existing classification_ids, handles alt_id merges, obsoletion, replacement. Rebuilds `go_classification_descendants` materialized view | ~minutes |
| 3 | `update_paint_go_annotation` | `go_annotation.sql` | Inserts new GO annotations, obsoletes removed ones, replaces terms via alt_id | **~1 hour** |
| 4 | `update_paint_go_evidence` | `go_evidence.sql` | Rebuilds GO evidence from `goanno_wf` with unnested evidence strings | ~17 min |
| 5 | `update_paint_go_annot_qualifier` | `go_annotation_qualifier.sql` | Updates annotation qualifiers (NOT, contributes_to, colocalizes_with) | ~minutes |
| 6 | `switch_evidence_to_pmid` | `switch_evidence_to_pmid.sql` | Converts evidence references to PubMed IDs | ~minutes |
| 7 | `delete_incorrect_go_annot_qualifiers` | `delete_incorrect_go_annot_qualifiers.sql` | Removes qualifier mismatches | ~minutes |
| 8 | `update_paint_paint_annotation` | `paint_annotation.sql` | Obsoletes PAINT annotations for obsoleted GO terms, replaces classification_ids for replaced terms | ~minutes |
| 9 | `update_paint_paint_evidence` | `paint_evidence.sql` | **Most complex SQL**: obsoletes unsupported PAINT_EXP evidence, inserts new evidence for IBDs by checking descendant terms, updates PAINT_ANCESTOR evidence, un-obsoletes paint_annotations that regain support | **~19 min** |
| 10 | `setup_preupdate_data` | (multiple) | Generates before-update GAFs for comparison | variable |
| 11 | `switch_paint_table_names` | `switch_table_names.sql` | Atomic swap of 13 table pairs | ~seconds |

### PAN-GO Pipeline (optional)

Separate pipeline for PAN-GO-specific tables:
- `load_raw_go_to_panther` (shared with PANTHER pipeline)
- `update_pango_new_tables` -- builds `pango_go_classification`, `pango_version`, `pango_genelist_agg`
- `switch_pango_table_names` -- atomic swap

### The paint_evidence.sql Deep Dive

This is the most critical and complex SQL in the system (122 lines, 4 major operations):

1. **Obsolete unsupported PAINT_EXP evidence**: For each `paint_evidence_new` record with `evidence_type_sid = 46` (PAINT_EXP), check if the referenced `go_annotation` still exists with a valid experimental evidence code and matching qualifier. If not, mark as obsoleted.

2. **Insert new valid evidence**: For each `paint_annotation_new`, find leaf nodes in the family tree, check if any have GO annotations to the same or descendant terms (via `go_classification_descendants`), with matching qualifiers and experimental evidence codes. Insert new `paint_evidence` records for novel supporting evidence.

3. **Update PAINT_ANCESTOR evidence**: For evidence records with `evidence_type_sid = 47` (PAINT_ANCESTOR), update the `evidence` column to point to the correct non-obsolete ancestor paint_annotation. Un-obsolete if the ancestor annotation is restored.

4. **Cascade obsoletions**: Obsolete `paint_annotation` records that no longer have any supporting non-obsolete `paint_evidence`. Then un-obsolete any `paint_annotation` that regains valid evidence.

## Phase 3: GAF Generation

### Resource Extraction from Database

Before GAF generation, current annotation data is queried from the database:

| Recipe | Query | Output File |
|--------|-------|-------------|
| `paint_annotation` | `paint_annotation.sql` | `resources/paint_annotation` |
| `paint_annotation_qualifier` | `paint_annotation_qualifier.sql` | `resources/paint_annotation_qualifier` |
| `paint_evidence` | `paint_evidence.sql` | `resources/paint_evidence` |
| `go_aggregate` | `go_aggregate.sql` | `resources/go_aggregate` |
| `paint_exp_aggregate` | `paint_exp_aggregate.sql` | `resources/paint_exp_aggregate` |
| `organism_taxon` | `organism_taxon.sql` | `resources/organism_taxon` |

### GAF Creation (`create_gafs`)

**Script**: `scripts/createGAF.pl` (invoked via `createGAF.sh`)

**Inputs** (10+ files):
- `profile.txt` -- version metadata
- `paint_annotation` -- IBD annotation records
- `paint_evidence` -- evidence supporting IBDs
- `paint_annotation_qualifier` -- qualifiers (NOT, contributes_to)
- `go_aggregate` -- all GO annotations per node
- `paint_exp_aggregate` -- experimental PAINT annotations
- `gene.dat` -- gene-to-node mappings
- `organism.dat` -- organism metadata
- `treeNodes/` -- per-family phylogenetic trees
- `goparentchild_isaonly.tsv` -- GO hierarchy
- `complex_terms.tsv` -- protein complex GO terms
- `panther_blacklist.txt` -- genes to exclude

**Process for each IBD annotation**:
1. Find the annotated node in the family tree
2. Traverse tree to find all descendant leaf genes
3. Exclude genes with IKR (Inferred from Key Residues) or IRD (Inferred from Rapid Divergence) evidence against this annotation
4. For each qualifying leaf gene, generate an IBA line
5. Apply qualifier validation: verify agreement between IBD qualifier and experimental evidence qualifier
6. Apply redundancy filtering: remove IBAs where a more specific GO term annotation exists for the same gene (or more general for NOT annotations)
7. Determine GAF 2.2 relation (enables, involved_in, is_active_in, part_of for complexes)
8. Map PANTHER long IDs to MOD-specific short IDs (FlyBase->FB, WormBase->WB, etc.)

**Output**: Per-organism GAF files in `IBA_GAFs/`:
- `gene_association.paint_human.gaf`
- `gene_association.paint_mgi.gaf`
- `gene_association.paint_fb.gaf`
- ... (13 model organisms)

**Variant outputs**:
- `create_gafs_goa` -- UniProt-only IDs (for GOA submission)
- `gene_association.paint_exp.gaf` -- PAINT experimental annotations

### Post-processing

- `fix_pombe_symbol.pl` -- Fixes PomBase gene symbols using current PomBase gene name files
- `gaf2pmid.pl` -- Extracts unique PMIDs for PubMed linkout generation

## Phase 4: Reporting and QC

### Before/After Comparison

The pipeline generates GAFs both before and after the GO update:
1. `setup_preupdate_data` captures pre-update state (queries DB, generates "before" GAFs)
2. `gen_iba_gaf_yamls` generates YAML configs pointing to before/after directories
3. `run_reports` runs comparison tools

### Reports Generated

| Tool | Output |
|------|--------|
| `iba_count.py` | IBA count diffs by family, before/after. Publishes to Google Sheets |
| `iba_count.py --mods_only` | Same but filtered to model organisms only |
| `version_paint_annot_counts.py` | Paint annotation count changes by family |
| `report_curation_status.py` | Current curation status by family |
| `created_ibds_by_curator.py` | IBDs created per curator in date range |
| `compare_paint_releases.py` | Comprehensive release comparison: new/obsoleted IBDs, added/dropped IBAs |

## Data Flow Summary

```
GO FTP -.gaf.gz files
  |
  v
gunzip -> .gaf files -> fullGoMappingPthrHierarchy.pl -> Pthr_GO.tsv
                                                            |
go.obo -> extractfromgoobo.pl -> inputforGOClassification.tsv
       -> extractfromgoobo_relation.pl -> goparentchild.tsv
                                            |
                              [COPY into PostgreSQL staging tables]
                                            |
                              [SQL update pipeline on _new tables]
                                            |
                              [Atomic table name swap]
                                            |
                              [Query DB -> resource files]
                                            |
                              createGAF.pl + tree files + gene.dat
                                            |
                                            v
                              IBA_GAFs/gene_association.paint_*.gaf
```

## Discussion Points

### No Idempotency Guarantees
Most pipeline steps are not idempotent. Re-running a step (e.g., after a failure) can produce incorrect results -- for example, double-inserting evidence records or corrupting the `_new`/`_old` table state. The `reset_paint_table.sh` script exists for manual recovery, but there is no automated rollback or retry logic.

### Implicit Ordering Dependencies
The Makefile recipes must be run in a specific order, but this ordering is not enforced by Make's dependency system. The recipes are all `.PHONY` targets with no declared prerequisites. Running them out of order will silently produce incorrect results or fail in confusing ways.

### Duration Variance
The `update_paint_go_annotation` step can take ~1 hour, and `update_paint_paint_evidence` ~19 minutes. These are database-bound operations whose duration depends on the size of the GO release delta. There is no progress indication or timeout handling.

### Data Integrity Window
Between `load_raw_go_to_paint` and `switch_paint_table_names`, the database is in an inconsistent state where `_new` tables have been modified but the live tables haven't been swapped. If the pipeline fails mid-way, manual intervention is required. The `run_paint_pipeline.sh` script tracks affected tables for this reason.

### Large Intermediate Files
The gene-to-PANTHER mapping step processes tens of GB of GAF data. The `goa_uniprot_all` file alone requires splitting at 300M lines. These intermediate files are stored in `$BASE_PATH/` but are never automatically cleaned up.

### Redundancy Filtering Complexity
The redundancy filtering in `createGAF.pl` is algorithmically complex: for each IBA, it must check whether a more specific GO term annotation exists for the same gene by traversing the GO hierarchy. This is O(n * m) where n is IBAs and m is GO term depth, mitigated by caching ancestor/descendant lookups.
