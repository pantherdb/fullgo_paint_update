from Bio import Phylo
import csv
import argparse
import logging

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

parser = argparse.ArgumentParser()
parser.add_argument("-o", "--output_file")
parser.add_argument("-s", "--slim_terms")
parser.add_argument("-t", "--taxon_term_table")
parser.add_argument("-p", "--panther_tree_nhx")
# args = parser.parse_args()

MADEUP_SPECIES = [
    "Saccharomycetaceae-Candida",
    "Alveolata-Stramenopiles",
    "Rhabditida-Chromadorea",
    "Metazoa-Choanoflagellida",
    "Pezizomycotina-Saccharomycotina",
    "Hexapoda-Crustacea",
    "Craniata-Cephalochordata",
    "Archaea-Eukaryota",
    "Fornicata-Parabasalids",
    "Homo-Pan",
    "Sordariomycetes-Leotiomycetes",
    "Opisthokonta",
    "Excavates",
    "Unikonts",
    "Artiodactyla",
    "LUCA"
]

def extract_clade_name(clade_comment):
    if clade_comment is None:
        clade_comment = ""
    new_comment = clade_comment.replace("&&NHX:S=", "")
    new_comment = new_comment.replace("&&NXH:S=", "")
    if new_comment == "Opisthokonts":
        new_comment = "Opisthokonta"
    return new_comment

def name_children(parent_clade):
    # print(parent_clade.name)
    for child in parent_clade.clades:
        child.name = extract_clade_name(child.comment)
        if len(child.clades) > 0:
            name_children(child)

def find_taxon_clade(taxon_name, root_clade):
    # print(root_clade)
    if root_clade.name == taxon_name:
        return root_clade
    elif len(root_clade.clades) > 0:
        for c in root_clade.clades:
            result = find_taxon_clade(taxon_name, c)
            if result is not None:
                return result


class TaxonTermValidator:
    def __init__(self, taxon_term_table, panther_tree_nhx, slim_terms=None):
        self.term_constraint_lists = {}
        self.taxon_indexes = {}
        self.slim_terms = []
        self.tree = None

        if slim_terms:
            # Get list of slim terms to filter for
            slim_file = open(slim_terms)
            for t in slim_file.readlines():
                self.slim_terms.append(t.rstrip())
            slim_file.close()
        
        with open(taxon_term_table) as t3f:
            header = t3f.readline().rstrip()
            headers = header.split("\t")
            index_count = 0
            for h in headers[1:len(headers)]:
                self.taxon_indexes[h] = index_count
                index_count += 1

            for l in t3f.readlines():
                cols = l.split("\t")
                go_term = cols[0]
                if len(self.slim_terms) == 0 or go_term in self.slim_terms:
                    self.term_constraint_lists[go_term] = cols[1:len(cols)]

        logger.debug("taxon_indexes: {}".format(len(self.taxon_indexes)))
        logger.debug("term_constraint_lists: {}".format(len(self.term_constraint_lists)))

        # Parse species_tree
        self.tree = next(Phylo.parse(panther_tree_nhx, "newick"))
        self.tree.clade.name = extract_clade_name(self.tree.clade.comment)
        name_children(self.tree.clade)

    def validate_taxon_term(self, taxon, term):
        # node_path[-2] won't work for LUCA. LUCA should equal NCBITaxon:131567 for "cellular organisms".
        # Need to rerun gaferencer to include this taxon, then convert "cellular organisms" header to "LUCA" in
        # taxon_to_oscode.py
        # print(taxon)
        while taxon in MADEUP_SPECIES and taxon != "LUCA":
            # print(taxon)
            # Get parent of taxon - handy BioPython trick
            taxon_clade = find_taxon_clade(taxon, self.tree.clade)
            node_path = self.tree.get_path(taxon_clade)
            if len(node_path) > 1:
                parent_clade = node_path[-2]
            else:
                parent_clade = self.tree.clade
            taxon = parent_clade.name

        # Remove after getting LUCA's real values - assuming most everything is cool with LUCA
        if taxon == "LUCA":
            # virus stuff
            if term in ("GO:0019012", "GO:0039679", "GO:0044423"):
                return False
            else:
                return True

        try:
            result = self.term_constraint_lists[term][self.taxon_indexes[taxon]]
        except IndexError:
            print(taxon)
            result = self.term_constraint_lists[term][self.taxon_indexes[taxon]]
        if result == '0':
            return False
        return True

def append_madeup_species_to_table(validator : TaxonTermValidator, output_file):
    # List hyphenated species
    # Reconstruct entire table file
    # with open("new_table_file", "w+") as nf:
    with open(output_file, "w+") as nf:
        writer = csv.writer(nf, delimiter="\t")
        header = ["GOterm"]
        out_term_values = {}
        for tk in list(validator.taxon_indexes.keys()) + MADEUP_SPECIES:
            header.append(tk)
            for term in validator.term_constraint_lists:
                if validator.validate_taxon_term(tk, term):
                    result = 1
                else:
                    result = 0
                if term in out_term_values:
                    out_term_values[term].append(result)
                else:
                    out_term_values[term] = [term, result]

        writer.writerow(header)
        for otv in out_term_values:
            if len(validator.slim_terms) == 0 or otv in validator.slim_terms:
                writer.writerow(out_term_values[otv])

if __name__ == "__main__":
    args = parser.parse_args()

    validator = TaxonTermValidator(args.taxon_term_table, args.panther_tree_nhx)
    append_madeup_species_to_table(validator, args.output_file)