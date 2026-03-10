# propagate_paint_ibas.py Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

> **Note (2026-03-06):** This plan and all associated files were originally created in `panther_build` and have been relocated to `fullgo_paint_update` since the IBA propagation process is more closely tied to the PAINT full GO release pipeline.

**Goal:** New script to propagate PAINT IBD GO annotations down same-version PANTHER library trees, producing a PAINT_Annotations_TOTAL.txt file.

**Architecture:** Parse a PAINT release GAF file (IBD=GAIN, IKR/IRD=NOT), map PTN IDs to PTHR:AN via node.dat, walk each family's NHX tree propagating a set of active GO terms, and write one output line per node. SF/PC annotations are read from annotation_treegrafter.dat. Reuses `pthr_db_caller.haiming_to_newick.ToNewick` for NHX->Newick conversion.

**Tech Stack:** Python 3, BioPython (Phylo), argparse, `pthr_db_caller` library (provides `haiming_to_newick` module).

**Design doc:** `.plans/2026-03-05-propagate-paint-ibas-design.md`

---

### Task 1: Create test fixtures for PTHR10000

**Files:**
- Create: `resources/test/ibd_PTHR10000.gaf` (small IBD GAF fixture)

**Step 1: Create a minimal IBD GAF test fixture**

This fixture covers PTHR10000 using real PTN IDs from `resources/test/node_19_PTHR10000.dat`:
- PTN000000084 = AN0 (root) — 3 IBD GO annotations (GO:0000287, GO:0005829, GO:0016791)
- One IKR NOT annotation at a descendant node to test blocking

```
!gaf-version: 2.1
!Test fixture for PTHR10000
PANTHER	PTN000000084	PTN000000084		GO:0016791	GO_REF:0000033	IBD	UniProtKB:P75792	F			protein	taxon:	20200807	GO_Central
PANTHER	PTN000000084	PTN000000084		GO:0005829	GO_REF:0000033	IBD	UniProtKB:P21829	C			protein	taxon:	20200129	GO_Central
PANTHER	PTN000000084	PTN000000084		GO:0000287	GO_REF:0000033	IBD	UniProtKB:P75792	F			protein	taxon:	20200807	GO_Central
PANTHER	PTN004118868	PTN004118868	NOT	GO:0005829	GO_REF:0000033	IKR	PANTHER:PTN000000084	C			protein	taxon:131567	20210101	GO_Central
```

PTN004118868 = AN3 (internal, child of AN2 which is child of AN1 which is child of AN0). The IKR NOT on GO:0005829 at AN3 should block that term from propagating to AN3's descendants while GO:0016791 and GO:0000287 continue.

**Step 2: Verify fixture PTNs match node.dat**

Run: `grep -E "PTN000000084|PTN004118868" resources/test/node_19_PTHR10000.dat`
Expected:
```
PTHR10000:AN0	PTN000000084	ROOT	SPECIATION	0
PTHR10000:AN3	PTN004118868	INTERNAL	SPECIATION	0.270
```

---

### Task 2: Write failing tests for parsing functions

**Files:**
- Create: `test_propagate_paint_ibas.py` (in repo root, alongside existing `test.py`)

**Step 1: Write failing tests for all three parsers**

```python
import pytest
from scripts.propagate_paint_ibas import parse_node_file, parse_ibd_gaf, parse_annotation_file_sf_pc


class TestParseNodeFile:
    def test_builds_ptn_to_an_mapping(self):
        ptn_to_an, an_to_ptn, families = parse_node_file("resources/test/node_19_PTHR10000.dat")
        assert ptn_to_an["PTN000000084"] == "PTHR10000:AN0"
        assert ptn_to_an["PTN004118868"] == "PTHR10000:AN3"

    def test_builds_an_to_ptn_mapping(self):
        ptn_to_an, an_to_ptn, families = parse_node_file("resources/test/node_19_PTHR10000.dat")
        assert an_to_ptn["PTHR10000:AN0"] == "PTN000000084"

    def test_extracts_families(self):
        ptn_to_an, an_to_ptn, families = parse_node_file("resources/test/node_19_PTHR10000.dat")
        assert "PTHR10000" in families


class TestParseIbdGaf:
    def test_parses_ibd_as_gains(self):
        gains, nots = parse_ibd_gaf("resources/test/ibd_PTHR10000.gaf", {"PTN000000084": "PTHR10000:AN0", "PTN004118868": "PTHR10000:AN3"})
        assert gains["PTHR10000:AN0"] == {"GO:0016791", "GO:0005829", "GO:0000287"}

    def test_parses_ikr_as_nots(self):
        gains, nots = parse_ibd_gaf("resources/test/ibd_PTHR10000.gaf", {"PTN000000084": "PTHR10000:AN0", "PTN004118868": "PTHR10000:AN3"})
        assert nots["PTHR10000:AN3"] == {"GO:0005829"}

    def test_skips_header_lines(self):
        gains, nots = parse_ibd_gaf("resources/test/ibd_PTHR10000.gaf", {"PTN000000084": "PTHR10000:AN0", "PTN004118868": "PTHR10000:AN3"})
        # Should not crash, and no annotations from header lines
        assert len(gains) == 1  # Only AN0 has IBD annotations


class TestParseAnnotationFileSfPc:
    def test_parses_sf_annotations(self):
        sf, pc = parse_annotation_file_sf_pc("resources/test/annotation_treegrafter_PTHR10000.dat")
        assert sf["PTHR10000:AN0"] == "SF8"
        assert sf["PTHR10000:AN72"] == "SF55"

    def test_ignores_go_lines(self):
        sf, pc = parse_annotation_file_sf_pc("resources/test/annotation_treegrafter_PTHR10000.dat")
        # GO lines should not appear in SF or PC results
        for key in sf:
            assert not sf[key].startswith("GO:")
```

**Step 2: Run tests to verify they fail**

Run: `pytest test_propagate_paint_ibas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.propagate_paint_ibas'`

---

### Task 3: Implement parsing functions

**Files:**
- Create: `scripts/propagate_paint_ibas.py`

**Step 1: Implement the three parsing functions and argparse skeleton**

```python
#!/usr/bin/env python3

import os
import sys
import argparse
from collections import defaultdict
from Bio import Phylo
from pthr_db_caller.haiming_to_newick import ToNewick


parser = argparse.ArgumentParser(description='Propagate PAINT IBD annotations down PANTHER trees')
parser.add_argument('-i', '--ibd_file', required=True, help='PAINT release IBD GAF file')
parser.add_argument('-t', '--tree_dir', required=True, help='Source tree directory of PANTHER NHX trees')
parser.add_argument('-a', '--annotation_file', required=True, help='annotation_treegrafter.dat (for SF/PC only)')
parser.add_argument('-n', '--node_file', required=True, help='node.dat file')
parser.add_argument('-o', '--output_file', required=True, help='Output filename (PAINT_Annotations_TOTAL.txt)')


def parse_node_file(node_file):
    """Parse node.dat, returning PTN->AN, AN->PTN mappings and set of families."""
    ptn_to_an = {}
    an_to_ptn = {}
    families = set()

    with open(node_file) as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                pthr_an = parts[0]
                ptn = parts[1]
                ptn_to_an[ptn] = pthr_an
                an_to_ptn[pthr_an] = ptn
                families.add(pthr_an.split(':')[0])

    return ptn_to_an, an_to_ptn, families


def parse_ibd_gaf(gaf_file, ptn_to_an):
    """Parse PAINT IBD GAF file. IBD -> gains, IKR/IRD with NOT -> nots."""
    gains = defaultdict(set)
    nots = defaultdict(set)

    with open(gaf_file) as f:
        for line in f:
            if line.startswith('!'):
                continue
            parts = line.strip().split('\t')
            if len(parts) < 7:
                continue

            ptn = parts[1]
            qualifier = parts[3]
            go_term = parts[4]
            evidence = parts[6]

            pthr_an = ptn_to_an.get(ptn)
            if pthr_an is None:
                continue

            if evidence == "IBD" and qualifier != "NOT":
                gains[pthr_an].add(go_term)
            elif evidence in ("IKR", "IRD") and qualifier == "NOT":
                nots[pthr_an].add(go_term)

    return gains, nots


def parse_annotation_file_sf_pc(annotation_file):
    """Parse annotation_treegrafter.dat for SF and PC annotations only."""
    sf_annotations = {}
    pc_annotations = defaultdict(set)

    with open(annotation_file) as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 3:
                continue

            node_an = parts[0]
            annot_type = parts[2]

            if annot_type == "SF":
                pthr_sf = parts[1]
                if ":" not in pthr_sf:
                    continue
                sf = pthr_sf.split(':', maxsplit=1)[1]
                sf_annotations[node_an] = sf
            elif annot_type == "PC":
                pthr_pc = parts[1]
                pc = pthr_pc.split(':', maxsplit=1)[1]
                pc_annotations[node_an].add(pc)

    return sf_annotations, pc_annotations
```

**Step 2: Run tests to verify they pass**

Run: `pytest test_propagate_paint_ibas.py -v`
Expected: All 7 tests PASS

**Step 3: Commit**

```
feat: add parsing functions for propagate_paint_ibas
```

---

### Task 4: Write failing test for tree propagation

**Files:**
- Modify: `test_propagate_paint_ibas.py`

**Step 1: Write failing test for propagate function**

```python
import os
import tempfile
from scripts.propagate_paint_ibas import parse_node_file, parse_ibd_gaf, parse_annotation_file_sf_pc, propagate_all


class TestPropagateAll:
    def setup_method(self):
        self.ptn_to_an, self.an_to_ptn, self.families = parse_node_file("resources/test/node_19_PTHR10000.dat")
        self.gains, self.nots = parse_ibd_gaf("resources/test/ibd_PTHR10000.gaf", self.ptn_to_an)
        self.sf, self.pc = parse_annotation_file_sf_pc("resources/test/annotation_treegrafter_PTHR10000.dat")

    def test_root_gets_all_ibd_terms(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            output_file = f.name
        try:
            propagate_all(
                families=self.families,
                tree_dir="resources/test/tree_19_PTHR10000",
                gains=self.gains,
                nots=self.nots,
                sf_annotations=self.sf,
                pc_annotations=self.pc,
                an_to_ptn=self.an_to_ptn,
                output_file=output_file,
            )
            lines = open(output_file).readlines()
            # Find AN0 (root) line
            root_lines = [l for l in lines if l.startswith("PTHR10000:AN0\t")]
            assert len(root_lines) == 1
            root_line = root_lines[0]
            assert "GO:0000287" in root_line
            assert "GO:0005829" in root_line
            assert "GO:0016791" in root_line
        finally:
            os.unlink(output_file)

    def test_not_blocks_propagation(self):
        """AN3 has IKR NOT on GO:0005829 — that term should not appear at AN3 or descendants."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            output_file = f.name
        try:
            propagate_all(
                families=self.families,
                tree_dir="resources/test/tree_19_PTHR10000",
                gains=self.gains,
                nots=self.nots,
                sf_annotations=self.sf,
                pc_annotations=self.pc,
                an_to_ptn=self.an_to_ptn,
                output_file=output_file,
            )
            lines = open(output_file).readlines()
            # AN3 should NOT have GO:0005829 but SHOULD have the other two
            an3_lines = [l for l in lines if l.startswith("PTHR10000:AN3\t")]
            assert len(an3_lines) == 1
            an3_line = an3_lines[0]
            assert "GO:0005829" not in an3_line
            assert "GO:0000287" in an3_line
            assert "GO:0016791" in an3_line

            # AN4 is child of AN3 — should also not have GO:0005829
            an4_lines = [l for l in lines if l.startswith("PTHR10000:AN4\t")]
            assert len(an4_lines) == 1
            assert "GO:0005829" not in an4_lines[0]
            assert "GO:0000287" in an4_lines[0]
        finally:
            os.unlink(output_file)

    def test_sf_annotation_inherited(self):
        """SF8 at AN0 should propagate down until overridden."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            output_file = f.name
        try:
            propagate_all(
                families=self.families,
                tree_dir="resources/test/tree_19_PTHR10000",
                gains=self.gains,
                nots=self.nots,
                sf_annotations=self.sf,
                pc_annotations=self.pc,
                an_to_ptn=self.an_to_ptn,
                output_file=output_file,
            )
            lines = open(output_file).readlines()
            # AN1 inherits SF8 from AN0
            an1_lines = [l for l in lines if l.startswith("PTHR10000:AN1\t")]
            assert len(an1_lines) == 1
            assert "PTHR10000:SF8" in an1_lines[0]

            # AN72 has SF55 override
            an72_lines = [l for l in lines if l.startswith("PTHR10000:AN72\t")]
            assert len(an72_lines) == 1
            assert "PTHR10000:SF55" in an72_lines[0]
        finally:
            os.unlink(output_file)

    def test_output_format_matches_total_txt(self):
        """Each line should be: PTHR:AN\\tPTHR:SF  GO:terms;  PC;\\tPTN"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            output_file = f.name
        try:
            propagate_all(
                families=self.families,
                tree_dir="resources/test/tree_19_PTHR10000",
                gains=self.gains,
                nots=self.nots,
                sf_annotations=self.sf,
                pc_annotations=self.pc,
                an_to_ptn=self.an_to_ptn,
                output_file=output_file,
            )
            lines = open(output_file).readlines()
            for line in lines:
                parts = line.strip().split('\t')
                assert len(parts) == 3, f"Expected 3 tab-separated columns, got {len(parts)}: {line.strip()}"
                assert parts[0].startswith("PTHR10000:")
                assert parts[2].startswith("PTN") or parts[2] == ""
        finally:
            os.unlink(output_file)

    def test_nodes_without_go_have_empty_go_field(self):
        """Nodes with no inherited or own GO terms should still appear with empty GO field."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            output_file = f.name
        try:
            propagate_all(
                families=self.families,
                tree_dir="resources/test/tree_19_PTHR10000",
                gains=self.gains,
                nots=self.nots,
                sf_annotations=self.sf,
                pc_annotations=self.pc,
                an_to_ptn=self.an_to_ptn,
                output_file=output_file,
            )
            lines = open(output_file).readlines()
            # All 186 nodes in node_19_PTHR10000.dat should have output lines
            node_count = sum(1 for _ in open("resources/test/node_19_PTHR10000.dat"))
            # +1 for the "PTHR:root" line if present, but at minimum all nodes
            assert len(lines) >= node_count
        finally:
            os.unlink(output_file)
```

**Step 2: Run tests to verify they fail**

Run: `pytest test_propagate_paint_ibas.py::TestPropagateAll -v`
Expected: FAIL — `ImportError: cannot import name 'propagate_all'`

---

### Task 5: Implement tree propagation and output

**Files:**
- Modify: `scripts/propagate_paint_ibas.py`

**Step 1: Add propagate_all function and tree walking logic**

Add after the parsing functions:

```python
def format_output_line(node_id, pthr, sf, active_go, pc, ptn):
    """Format a single output line matching PAINT_Annotations_TOTAL.txt format."""
    sf_str = f"PTHR{pthr.replace('PTHR', '')}:{sf}" if sf else ""
    go_str = ";".join(sorted(active_go)) + ";" if active_go else ""
    pc_str = ";".join(sorted(pc)) + ";" if pc else ""
    compound = f"{sf_str}  {go_str}  {pc_str}"
    return f"{node_id}\t{compound}\t{ptn}\n"


def walk_tree(node, pthr, inherited_go, inherited_sf, inherited_pc,
              gains, nots, sf_annotations, pc_annotations, an_to_ptn, out_file):
    """Recursively walk tree, propagating GO terms and writing output."""
    node_id = f"{pthr}:{node.name}" if node.name else f"{pthr}:unnamed"

    # Compute active GO set
    active_go = set(inherited_go)
    active_go |= gains.get(node_id, set())
    active_go -= nots.get(node_id, set())

    # SF: inherit or override
    sf = sf_annotations.get(node_id, inherited_sf)

    # PC: accumulate
    pc = set(inherited_pc)
    pc |= pc_annotations.get(node_id, set())

    ptn = an_to_ptn.get(node_id, "")
    out_file.write(format_output_line(node_id, pthr, sf, active_go, pc, ptn))

    for child in node.clades:
        walk_tree(child, pthr, active_go, sf, pc,
                  gains, nots, sf_annotations, pc_annotations, an_to_ptn, out_file)


def propagate_all(families, tree_dir, gains, nots, sf_annotations,
                  pc_annotations, an_to_ptn, output_file):
    """Propagate IBD annotations through all family trees."""
    to_newick = ToNewick()

    with open(output_file, 'w') as out_file:
        for pthr in sorted(families):
            tree_file = os.path.join(tree_dir, f"{pthr}.tree")
            if not os.path.exists(tree_file):
                continue

            # Convert NHX to newick in a temp location
            newick_file = tree_file + ".newick"
            if not os.path.exists(newick_file) or os.path.getsize(newick_file) == 0:
                to_newick.tonewick_only_an(tree_file, newick_file)

            try:
                tree = Phylo.read(newick_file, "newick")
            except Exception as e:
                print(f"Error reading tree {newick_file}: {e}", file=sys.stderr)
                continue

            root = tree.root
            if not root.name and len(root.clades) > 0:
                root = root.clades[0]

            walk_tree(root, pthr, set(), "", set(),
                      gains, nots, sf_annotations, pc_annotations, an_to_ptn, out_file)
```

**Step 2: Run tests to verify they pass**

Run: `pytest test_propagate_paint_ibas.py -v`
Expected: All tests PASS

**Step 3: Commit**

```
feat: add tree propagation and output for propagate_paint_ibas
```

---

### Task 6: Add CLI main block

**Files:**
- Modify: `scripts/propagate_paint_ibas.py`

**Step 1: Add main block after propagate_all**

```python
if __name__ == "__main__":
    args = parser.parse_args()

    print("Parsing node file...")
    ptn_to_an, an_to_ptn, families = parse_node_file(args.node_file)

    print("Parsing IBD GAF file...")
    gains, nots = parse_ibd_gaf(args.ibd_file, ptn_to_an)
    print(f"  {sum(len(v) for v in gains.values())} IBD annotations across {len(gains)} nodes")
    print(f"  {sum(len(v) for v in nots.values())} NOT annotations across {len(nots)} nodes")

    print("Parsing annotation file for SF/PC...")
    sf_annotations, pc_annotations = parse_annotation_file_sf_pc(args.annotation_file)

    print(f"Propagating through {len(families)} families...")
    propagate_all(
        families=families,
        tree_dir=args.tree_dir,
        gains=gains,
        nots=nots,
        sf_annotations=sf_annotations,
        pc_annotations=pc_annotations,
        an_to_ptn=an_to_ptn,
        output_file=args.output_file,
    )
    print(f"Done. Output written to {args.output_file}")
```

**Step 2: Smoke test the CLI with test fixtures**

Run:
```bash
python scripts/propagate_paint_ibas.py \
  -i resources/test/ibd_PTHR10000.gaf \
  -t resources/test/tree_19_PTHR10000 \
  -a resources/test/annotation_treegrafter_PTHR10000.dat \
  -n resources/test/node_19_PTHR10000.dat \
  -o /tmp/test_paint_total.txt
```
Expected: Script completes, output file written. Verify with:
```bash
head -5 /tmp/test_paint_total.txt
```
Should show lines in `PTHR:AN\tSF  GO:terms;  PC;\tPTN` format.

**Step 3: Commit**

```
feat: add CLI interface for propagate_paint_ibas
```

---

### Task 7: Run full test suite

**Step 1: Run all tests**

Run: `pytest test_propagate_paint_ibas.py test.py -v`
Expected: All tests PASS (existing tests unaffected)

**Step 2: Clean up any temp newick files created during tests**

Check for and remove any `.newick` files created in `resources/test/tree_19_PTHR10000/` during testing.
