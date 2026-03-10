# Design: propagate_paint_ibas.py

## Purpose

Generate a PAINT_Annotations_TOTAL.txt file by propagating IBD GO annotations from a PAINT release file down same-version PANTHER library trees as IBAs. Avoids the cross-version annotation forward-tracking complexity of precompute.py by requiring the IBD file and tree files to be from the same PANTHER library version.

## Inputs

| Flag | File | Purpose |
|------|------|---------|
| `-i` / `--ibd_file` | PAINT IBD GAF 2.1 file | IBD lines = GAIN; IKR/IRD lines with NOT qualifier = block propagation |
| `-t` / `--tree_dir` | NHX tree directory | Same PANTHER library version as IBD file |
| `-a` / `--annotation_file` | `annotation_treegrafter.dat` | SF and PC annotations only (GO lines ignored) |
| `-n` / `--node_file` | `node.dat` | PTN <-> PTHR:AN mapping |
| `-o` / `--output_file` | Output filename | Single file, all nodes (leaf + internal) |

## Output Format

Same as existing PAINT_Annotations_TOTAL.txt:

```
PTHR10000:AN0\tPTHR10000:SF8  GO:0000287;GO:0005829;  PC00195;\tPTN000000084
```

Columns (tab-separated):
1. `PTHR:AN` node identifier
2. Compound field (space-separated): `PTHR:SF`, `GO:terms;`, `PC;`
3. PTN identifier

## Core Algorithm

### Parsing

1. **node.dat** - Build `ptn_to_an` (PTN -> PTHR:AN) and `an_to_ptn` (PTHR:AN -> PTN) lookups. Extract set of families from PTHR prefixes.

2. **IBD GAF file** - For each non-header line:
   - IBD lines (GAF col 4 != "NOT"): `gains[pthr_an].add(go_term)`
   - IKR/IRD lines (GAF col 4 == "NOT"): `nots[pthr_an].add(go_term)`
   - Skip IBA lines and header lines (starting with `!`)

3. **annotation_treegrafter.dat** - Only SF and PC lines:
   - `sf_annotations[pthr_an]` = SF id
   - `pc_annotations[pthr_an]` = set of PC ids
   - GO lines ignored (GO annotations come from IBD file)

### Tree Walk (per family)

```
walk(node, inherited_go, inherited_sf, inherited_pc):
    node_id = f"{pthr}:{node.name}"

    # Compute this node's active GO set
    active_go = inherited_go | gains.get(node_id, set())
    active_go = active_go - nots.get(node_id, set())

    # SF/PC: inherit from ancestor, override at annotated nodes
    sf = sf_annotations.get(node_id, inherited_sf)
    pc = inherited_pc | pc_annotations.get(node_id, set())

    # Write output line
    ptn = an_to_ptn.get(node_id, "")
    write_line(node_id, sf, active_go, pc, ptn)

    for child in node.children:
        walk(child, active_go, sf, pc)
```

Key simplification: no GAIN/NOT string accumulation or process_instance() conflict resolution. Just a set of active GO terms that grows via IBD and shrinks via IKR/IRD.

### Output

Single file containing all nodes (leaf and internal), one line per node with accumulated GO terms.

## Dependencies

- `pthr_db_caller.haiming_to_newick.ToNewick` (NHX -> Newick conversion, provided by pthr_db_caller library)
- `Bio.Phylo` (BioPython)
- No new dependencies

## What This Does NOT Do

- No annotation forward-tracking between library versions
- No evidence gene propagation (the `-e` mode from precompute.py)
- No TreeGrafter-specific GO logic
- No `annotation_qualifier.dat` needed - NOTs come from IKR/IRD lines in the GAF file
