from scripts.iba_count import parse_and_load_node
import unittest

class TestIbaCount(unittest.TestCase):

    def test_loading_node_lookup(self):
        lkp = {}
        lkp = parse_and_load_node(lkp, 24, "resources/test/node_a.dat")
        lkp = parse_and_load_node(lkp, 26, "resources/test/node_b.dat")

        # print(lkp[26]["PTN001983924"])
        self.assertEqual(lkp[24]["PTN001983924"], "PTHR28584")
        self.assertEqual(lkp[26]["PTN001983924"], "PTHR18392")


if __name__ == '__main__':
    unittest.main()