# Testing

## Current Test Suite

The project has two test files covering a small fraction of the codebase.

### Unit Tests (`test.py`)

**Location**: Project root

**Run with**: `python test.py`

**Framework**: `unittest`

**Tests**:

#### `TestIbaCount.test_loading_node_lookup`
Tests `parse_and_load_node()` from `scripts/iba_count.py`:
- Loads `node_a.dat` and `node_b.dat` test fixtures (binary-ish PANTHER node files)
- Verifies that PTN (PANTHER Tree Node) IDs map to the correct family IDs across different classification versions
- Asserts: `PTN001983924` maps to `PTHR28584` in version 24 and `PTHR18392` in version 26

This tests a utility function, not a core pipeline component.

#### `TestTreeParser.test_get_descendants`
Tests `PantherTreeGraph` from `scripts/panther_tree_graph.py` (or `pthr_db_caller`):
- Loads tree file for family `PTHR10192` from `resources/tree_files/`
- Exercises: `edges()`, `nodes`, `predecessors()`, `ancestors()`, `descendants()`, `nodes_between()`
- **No assertions** -- uses `print()` statements only. This is effectively a manual inspection test, not an automated test.

**Fixture files**:
- `resources/test/node_a.dat` (159 bytes)
- `resources/test/node_b.dat` (159 bytes)
- `resources/tree_files/PTHR10192.tree` (requires external tree files)

### Integration Tests (`tests/test_gaferencer.py`)

**Location**: `tests/`

**Run with**: `pytest tests/test_gaferencer.py`

**Framework**: `pytest` with `parametrize`

**Requirements**: Live database connection via `pthr_db_caller`

**Tests**:

#### `test_taxon_term_combos` (parameterized, 12 cases)
Tests `TaxonTermValidator` from `pthr_db_caller.taxon_validate`:
- Loads test cases from `resources/test/gaferencer_test_cases.tsv`
- Each case: `(taxon_id, go_term, expected_0_or_1)`
- Validates that taxon-term combinations are correctly allowed/disallowed
- Hardcodes `taxa_table_20210416` as the lookup table name

**Fixture file**: `resources/test/gaferencer_test_cases.tsv` (12 test cases, 343 bytes)

## What Is Tested

| Component | Coverage |
|-----------|----------|
| `iba_count.parse_and_load_node()` | 1 test case |
| `PantherTreeGraph` traversal methods | Print-only, no assertions |
| `TaxonTermValidator.taxon_term_lookup()` | 12 parameterized cases |

## What Is NOT Tested

### Critical Untested Components

| Component | Risk Level | Why It Matters |
|-----------|------------|----------------|
| **`createGAF.pl`** (40KB) | **Critical** | Core GAF generation logic: tree traversal, redundancy filtering, qualifier validation, ID mapping. A bug here produces incorrect IBA annotations distributed to the community. |
| **All SQL update scripts** | **Critical** | The PAINT evidence update (`paint_evidence.sql`, 122 lines) is the most complex SQL in the system. A logic error silently corrupts curator annotations. |
| **`fullGoMappingPthrHierarchy.pl`** | **High** | Gene-to-PANTHER mapping with multi-strategy fallback. Incorrect mapping means genes assigned to wrong families. |
| **`extractfromgoobo.pl`** / **`extractfromgoobo_relation.pl`** | **High** | Ontology parsing. Incorrect parsing propagates through entire pipeline. |
| **`download_goex.py`** | **Medium** | Download logic with URL construction, directory listing scraping. |
| **`db_caller.py`** / `pthr_db_caller` integration | **Medium** | SQL variable substitution, connection management. |
| **`obsolete_redundant_ibds.py`** | **High** | Directly obsoletes curator annotations. Logic error = lost curation work. |
| **`paint_exp_to_gaf.py`** | **Medium** | Complex GAF formatting with OAK ontology integration. |

### Untested Behaviors

- **End-to-end pipeline correctness**: No test verifies that the full pipeline produces correct output given known input.
- **SQL update idempotency**: No test verifies behavior when a step is run twice.
- **Error conditions**: No tests for malformed input files, network failures, DB connection errors.
- **Table swap atomicity**: No test verifies the rename-swap pattern works correctly under concurrent access.
- **Redundancy filtering**: The most algorithmically complex part of `createGAF.pl` has no test coverage.
- **Qualifier validation**: The qualifier agreement logic between IBD and experimental annotations has no tests.
- **GO term replacement/merge handling**: The `go_classification.sql` logic for handling alt_ids and replaced_by terms is untested.

## Test Infrastructure

### No CI/CD
There is no continuous integration. Tests are run manually by developers.

### No Test Database
Integration tests require a live database connection. There is no test database fixture, no Docker Compose setup, no database seeding script.

### No Mocking
The test suite doesn't use mocks. The `TestTreeParser` test requires actual tree files. The gaferencer test requires a live database with the `taxa_table_20210416` table populated.

### No Test for Perl Scripts
The Perl scripts (which contain the most critical business logic) have zero test coverage. There is no Perl test framework configured.

## Existing QC Mechanisms (Not Tests)

The pipeline includes several QC mechanisms that serve as manual verification but are not automated tests:

| Mechanism | Purpose |
|-----------|---------|
| `wc -l` after ontology parsing | Sanity check on extracted term/relationship counts |
| `raw_table_count` / `panther_table_count` | Before/after row counts on loaded tables |
| `iba_count.py` | Before/after IBA count comparison |
| `compare_paint_releases.py` | Comprehensive release diff |
| `version_paint_annot_counts.py` | Annotation count changes by family |
| `check_dups` | Duplicate detection in GO classification |
| `scripts/sql/test/*.sql` | Ad-hoc verification queries (GO merge, evidence codes, dates) |

These are valuable but require human interpretation. None produce pass/fail results.

## Discussion Points

### Critical Gap: No Perl Testing
The Perl scripts contain the most complex and critical logic (createGAF.pl is 40KB of procedural code handling tree traversal, redundancy filtering, and ID mapping). Yet they have zero test coverage. This is the highest-risk testing gap.

Possible approaches:
- Add Perl unit tests (Test::More) for core subroutines
- Port critical logic to Python with tests
- Create golden-file tests: run createGAF.pl on known input, compare output to expected GAF

### Critical Gap: No SQL Testing
The SQL update scripts modify production databases without any prior testing. The `paint_evidence.sql` file alone has 4 complex operations that could silently corrupt data.

Possible approaches:
- Create a test database with known state
- Run SQL on test DB, verify expected mutations
- Use pgTAP or similar SQL testing framework

### `TestTreeParser` Has No Assertions
The tree parser test prints output but never asserts anything. It will always pass. This gives false confidence.

### Hardcoded Test Data
- `gaferencer_test_cases.tsv` uses a hardcoded table name (`taxa_table_20210416`)
- Tree files are expected at `resources/tree_files/` but this directory is not in the repo
- The test fixtures are minimal (159-byte node files, 12 gaferencer cases)

### No Regression Testing
When bugs are found and fixed, there is no mechanism to add regression tests. The pipeline's correctness relies on manual comparison of before/after outputs and operator experience.

### Suggested Priority for New Tests

1. **Golden-file test for `createGAF.pl`**: Given a small known tree, gene.dat, and annotation set, verify the output GAF exactly matches expected output. This is the single highest-value test that could be added.

2. **SQL update tests on a test database**: Load a small known dataset, run the update SQL, verify the expected rows were inserted/updated/obsoleted.

3. **Ontology parsing tests**: Feed known go.obo snippets through `extractfromgoobo.pl`, verify correct TSV output.

4. **End-to-end smoke test**: Even a minimal version (1 family, 1 organism) that exercises the full pipeline would catch integration issues.

5. **Fix `TestTreeParser`**: Add actual assertions to the existing test.
