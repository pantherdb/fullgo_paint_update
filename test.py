from scripts.iba_count import parse_and_load_node
from scripts.panther_tree_graph import PantherTreeGraph
import unittest
import networkx


class TestIbaCount(unittest.TestCase):

    def test_loading_node_lookup(self):
        lkp = {}
        lkp = parse_and_load_node(lkp, 24, "resources/test/node_a.dat")
        lkp = parse_and_load_node(lkp, 26, "resources/test/node_b.dat")

        # print(lkp[26]["PTN001983924"])
        self.assertEqual(lkp[24]["PTN001983924"], "PTHR28584")
        self.assertEqual(lkp[26]["PTN001983924"], "PTHR18392")


class TestTreeParser(unittest.TestCase):

    def test_get_descendants(self):
        # family = "PTHR10000"
        family = "PTHR10192"
        tree = PantherTreeGraph("resources/tree_files/{}.tree".format(family))
        for u, v in tree.edges():
            print(u, v)
            break

        print(tree.nodes['AN0'])
        print(list(tree.predecessors("AN5")))
        print(list(networkx.ancestors(tree, "AN5")))
        print(tree.descendants("AN0"))
        print(tree.nodes_between("AN2", "AN15"))
        # print(tree.phylo.tree)


if __name__ == '__main__':
    unittest.main()