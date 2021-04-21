import pytest
import csv
from pthr_db_caller.taxon_validate import TaxonTermValidator


taxon_term_table = "taxa_table_20210416"
validator = TaxonTermValidator(taxon_term_table)

test_cases = []
with open("resources/test/gaferencer_test_cases.tsv") as tcf:
    reader = csv.reader(tcf, delimiter="\t")
    for r in reader:
        test_cases.append(tuple(r))


@pytest.mark.parametrize("taxon,term,expected", test_cases)
def test_taxon_term_combos(taxon, term, expected):
    result = validator.taxon_term_lookup(taxon, term)
    assert int(result) == int(expected)
