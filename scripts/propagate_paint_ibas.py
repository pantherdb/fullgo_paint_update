#!/usr/bin/env python3

import os
import sys
import argparse
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

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


def format_output_line(node_id, pthr, sf, active_go, pc, ptn):
    """Format a single output line matching PAINT_Annotations_TOTAL.txt format."""
    sf_str = f"{pthr}:{sf}" if sf else ""
    go_str = ";".join(sorted(active_go)) + ";" if active_go else ""
    pc_str = ";".join(sorted(pc)) + ";" if pc else ""
    compound = f"{sf_str}  {go_str}  {pc_str}"
    return f"{node_id}\t{compound}\t{ptn}\n"


def walk_tree(node, pthr, inherited_go, inherited_sf, inherited_pc,
              gains, nots, sf_annotations, pc_annotations, an_to_ptn, out_file):
    """Recursively walk tree, propagating GO terms and writing output."""
    node_id = f"{pthr}:{node.name}" if node.name else f"{pthr}:unnamed"

    active_go = set(inherited_go)
    active_go |= gains.get(node_id, set())
    active_go -= nots.get(node_id, set())

    sf = sf_annotations.get(node_id, inherited_sf)

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
