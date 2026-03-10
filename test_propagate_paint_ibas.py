import os
import tempfile
import pytest
from scripts.propagate_paint_ibas import parse_node_file, parse_ibd_gaf, parse_annotation_file_sf_pc, propagate_all


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
        assert len(gains) == 1  # Only AN0 has IBD annotations


class TestParseAnnotationFileSfPc:
    def test_parses_sf_annotations(self):
        sf, pc = parse_annotation_file_sf_pc("resources/test/annotation_treegrafter_PTHR10000.dat")
        assert sf["PTHR10000:AN0"] == "SF8"
        assert sf["PTHR10000:AN72"] == "SF55"

    def test_ignores_go_lines(self):
        sf, pc = parse_annotation_file_sf_pc("resources/test/annotation_treegrafter_PTHR10000.dat")
        for key in sf:
            assert not sf[key].startswith("GO:")


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
            root_lines = [l for l in lines if l.startswith("PTHR10000:AN0\t")]
            assert len(root_lines) == 1
            root_line = root_lines[0]
            assert "GO:0000287" in root_line
            assert "GO:0005829" in root_line
            assert "GO:0016791" in root_line
        finally:
            os.unlink(output_file)

    def test_not_blocks_propagation(self):
        """AN3 has IKR NOT on GO:0005829"""
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
            an3_lines = [l for l in lines if l.startswith("PTHR10000:AN3\t")]
            assert len(an3_lines) == 1
            an3_line = an3_lines[0]
            assert "GO:0005829" not in an3_line
            assert "GO:0000287" in an3_line
            assert "GO:0016791" in an3_line

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
            an1_lines = [l for l in lines if l.startswith("PTHR10000:AN1\t")]
            assert len(an1_lines) == 1
            assert "PTHR10000:SF8" in an1_lines[0]

            an72_lines = [l for l in lines if l.startswith("PTHR10000:AN72\t")]
            assert len(an72_lines) == 1
            assert "PTHR10000:SF55" in an72_lines[0]
        finally:
            os.unlink(output_file)

    def test_output_format_matches_total_txt(self):
        """Each line: PTHR:AN\tcompound_field\tPTN"""
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

    def test_all_tree_nodes_present(self):
        """All nodes in the tree should have output lines."""
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
            node_count = sum(1 for _ in open("resources/test/node_19_PTHR10000.dat"))
            assert len(lines) >= node_count
        finally:
            os.unlink(output_file)
