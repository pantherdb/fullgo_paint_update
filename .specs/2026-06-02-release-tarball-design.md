# Release Tarball Recipe — Design

Date: 2026-06-02

## Purpose

Add a Makefile recipe that bundles the final outputs of a fullgo / PAINT update
release into a single distributable tarball. Today these artifacts are scattered
across `BASE_PATH` and need to be hand-renamed, hand-gzipped, and hand-tarred.

## Inputs (sources in `$(BASE_PATH)`)

| Source path                                       | In tarball as                                  | Gzipped?         |
|---------------------------------------------------|------------------------------------------------|------------------|
| `IBD`                                             | `IBD.gaf`                                      | No               |
| `PAINT_TreeGrafter_Annotations_TOTAL.txt`         | `PAINT_TreeGrafter_Annotations_TOTAL.txt.gz`   | Yes              |
| `gene_association.paint_uniprot.gaf`              | `gene_association.paint_uniprot.gaf.gz`        | Yes              |
| `IBA_GAFs/*.gaf`                                  | `presubmission/<file>.gaf.gz`                  | Yes (per file)   |

Each source path must exist; missing inputs abort the recipe.

## Output

`$(BASE_PATH)/$(TODAYS_DATE)_release.tar.gz` where `TODAYS_DATE := $(shell date +%Y-%m-%d)`.

The archive's top-level directory is `$(TODAYS_DATE)_release/`, so extraction
yields a self-contained release folder:

```
2026-06-02_release/
  IBD.gaf
  PAINT_TreeGrafter_Annotations_TOTAL.txt.gz
  gene_association.paint_uniprot.gaf.gz
  presubmission/
    gene_association.paint_human.gaf.gz
    gene_association.paint_mgi.gaf.gz
    ...   # one .gaf.gz per .gaf file found in IBA_GAFs/
```

## Variables added to Makefile

```make
TODAYS_DATE       ?= $(shell date +%Y-%m-%d)
RELEASE_DIR_NAME   = $(TODAYS_DATE)_release
RELEASE_STAGING    = $(BASE_PATH)/release_staging/$(RELEASE_DIR_NAME)
RELEASE_TARBALL    = $(BASE_PATH)/$(TODAYS_DATE)_release.tar.gz
```

`TODAYS_DATE` uses `?=` so callers can pin it (`make release_tarball TODAYS_DATE=2026-06-01`)
when packaging a release on a different day than the artifacts were generated.

## Dependencies (file-target shims)

`release_tarball` declares its inputs as prerequisites so a fresh checkout can
build them automatically, while a re-run on a complete `BASE_PATH` skips all
upstream work. Each input is wired through a thin shim with **no prerequisites**
that delegates to the existing producer recipe via sub-make. With no prereqs,
`make` skips the shim entirely when the file is present — exactly the
"don't regenerate every time" behavior we want.

| Prerequisite                                                | Producer recipe          |
|-------------------------------------------------------------|--------------------------|
| `$(BASE_PATH)/IBD` (also produces `IBA_GAFs/*.gaf`)         | `create_gafs`            |
| `$(TREEGRAFTER_ANNOTATIONS_TOTAL)`                          | `propagate_paint_ibas`   |
| `$(BASE_PATH)/gene_association.paint_uniprot.gaf`           | `create_gafs_goa`        |

```make
$(BASE_PATH)/IBD:
	$(MAKE) create_gafs

# propagate_paint_ibas reads $(BASE_PATH)/IBD (via TREEGRAFTER_IBD_GAF)
$(TREEGRAFTER_ANNOTATIONS_TOTAL): $(BASE_PATH)/IBD
	$(MAKE) propagate_paint_ibas

# create_gafs_goa reads SQL-query result files in $(BASE_PATH)/resources/
# that create_gafs writes alongside IBD
$(BASE_PATH)/gene_association.paint_uniprot.gaf: $(BASE_PATH)/IBD
	$(MAKE) create_gafs_goa

release_tarball: $(BASE_PATH)/IBD $(TREEGRAFTER_ANNOTATIONS_TOTAL) $(BASE_PATH)/gene_association.paint_uniprot.gaf
	...
```

### Ordering

Both `$(TREEGRAFTER_ANNOTATIONS_TOTAL)` and `$(BASE_PATH)/gene_association.paint_uniprot.gaf`
declare `$(BASE_PATH)/IBD` as a regular prerequisite (not order-only). This
captures the real causal relationship:

- `propagate_paint_ibas` reads `$(BASE_PATH)/IBD` as input.
- `create_gafs_goa` reads SQL-query result files in `$(BASE_PATH)/resources/`
  (e.g. `paint_annotation`, `paint_evidence`, `go_aggregate`) that
  `create_gafs` writes as part of producing `IBD`.

Using a regular prereq instead of an order-only (`|`) prereq has a useful
side effect: if `IBD` is ever rebuilt and ends up newer than the downstream
artifacts (e.g. someone deletes `IBD` and reruns), Make will treat the
downstream files as stale and rebuild them too — which is correct, because
they were derived from now-stale `resources/`.

### Notes

- `IBA_GAFs/*.gaf` are produced by `create_gafs` alongside `IBD`, so `IBD` serves
  as the sentinel for both. The preflight check still verifies the directory
  has GAFs to guard against a partially-deleted `IBA_GAFs/`.
- An explicit rule for `$(BASE_PATH)/gene_association.paint_uniprot.gaf` takes
  precedence over the pre-existing pattern rule
  `%/gene_association.paint_uniprot.gaf:` for this one path only. The pattern
  rule remains in effect for other paths (e.g.
  `preupdate_data/gene_association.paint_uniprot.gaf`).
- To force regeneration: delete the artifact (`rm $(BASE_PATH)/IBD`) and rerun
  `make release_tarball`, or invoke the producer recipe directly.
- Phony prereqs are intentionally **not** wired into the shims. The producer
  recipes already chain their own deps (DB queries, downloads, etc.) when they
  run; pulling those deps onto the shims would defeat the skip-when-present
  behavior because phony targets are always considered out-of-date.

## Recipe behavior

1. **Preflight checks**. For each required source path, fail with a clear
   message if missing:
   - `$(BASE_PATH)/IBD`
   - `$(BASE_PATH)/PAINT_TreeGrafter_Annotations_TOTAL.txt`
   - `$(BASE_PATH)/gene_association.paint_uniprot.gaf`
   - `$(BASE_PATH)/IBA_GAFs/` (and that at least one `*.gaf` lives inside)
2. **Prepare staging**. `rm -rf $(RELEASE_STAGING)` to wipe any prior partial
   run, then `mkdir -p $(RELEASE_STAGING)/presubmission`.
3. **Stage the files** (copies — originals are not modified):
   - `cp $(BASE_PATH)/IBD $(RELEASE_STAGING)/IBD.gaf`
   - `cp $(BASE_PATH)/PAINT_TreeGrafter_Annotations_TOTAL.txt $(RELEASE_STAGING)/` then `gzip` it
   - `cp $(BASE_PATH)/gene_association.paint_uniprot.gaf $(RELEASE_STAGING)/` then `gzip` it
   - For each `$(BASE_PATH)/IBA_GAFs/*.gaf`:
     `cp` into `$(RELEASE_STAGING)/presubmission/` then `gzip`
4. **Pack**:
   `tar -czf $(RELEASE_TARBALL) -C $(BASE_PATH)/release_staging $(RELEASE_DIR_NAME)`
5. **Clean up**: `rm -rf $(BASE_PATH)/release_staging`
6. **Report**: echo the tarball path and its size.

## Design decisions / trade-offs

- **Staging dir vs. in-place gzip**. We stage so the recipe is re-runnable and
  non-destructive — re-running the pipeline doesn't require regenerating
  artifacts that were already gzipped, and the original `.txt`/`.gaf` files
  remain available for inspection.
- **`.tar.gz` outer extension despite pre-gzipped contents**. The contents are
  already compressed, so the outer gzip adds little. We keep `.tar.gz` to match
  the project's existing `_fullgo.tar.gz` archives — convention over the few
  bytes of compression overhead. Pre-gzipped inner files also let consumers
  extract one GAF without inflating the whole archive.
- **`IBD.gaf` left uncompressed**. Per spec — it is the canonical IBD GAF and
  consumers expect plain text.
- **Fail loudly on missing inputs**. A partial release tarball is worse than no
  tarball; the recipe should not silently skip artifacts.
- **`cp` + `gzip` rather than `gzip -c < src > dst.gz`**. Equivalent on disk,
  but the two-step form keeps the Makefile recipe legible.

## Out of scope

- Uploading the tarball anywhere (FTP, S3, release hosting). The existing
  `push_gafs_to_ftp` target stub is the place for that and remains separate.
- Generating any of the source files. The recipe assumes the standard pipeline
  has produced them via `create_gafs`, `propagate_paint_ibas`, etc.
- A `.PHONY` cleanup target. The recipe self-cleans its staging dir on success.
