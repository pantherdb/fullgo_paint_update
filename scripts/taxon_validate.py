from Bio import Phylo
import csv
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-o", "--output_file")
parser.add_argument("-s", "--slim_terms")
parser.add_argument("-t", "--taxon_term_table")
args = parser.parse_args()

# taxon_term_file = "taxon_term_table_converted"
taxon_term_file = "TaxonConstraintsLookup.txt"

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

slim_terms = []
if args.slim_terms:
    # Get list of slim terms to filter for
    slim_file = open(args.slim_terms)
    for t in slim_file.readlines():
        slim_terms.append(t.rstrip())
    slim_file.close()

taxon_indexes = {}
term_constraint_lists = {}
with open(taxon_term_file) as t3f:
    header = t3f.readline().rstrip()
    headers = header.split("\t")
    index_count = 0
    for h in headers[1:len(headers)]:
        taxon_indexes[h] = index_count
        index_count += 1

    for l in t3f.readlines():
        cols = l.split("\t")
        go_term = cols[0]
        if len(slim_terms) == 0 or go_term in slim_terms:
            term_constraint_lists[go_term] = cols[1:len(cols)]

print("taxon_indexes: {}".format(len(taxon_indexes)))
print("term_constraint_lists: {}".format(len(term_constraint_lists)))

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

# Parse species_tree
tree = next(Phylo.parse("resources/species_pthr13_annot.nhx","newick"))
tree.clade.name = extract_clade_name(tree.clade.comment)
name_children(tree.clade)

def validate_taxon_term(taxon, term):
    # node_path[-2] won't work for LUCA. LUCA should equal NCBITaxon:131567 for "cellular organisms".
    # Need to rerun gaferencer to include this taxon, then convert "cellular organisms" header to "LUCA" in
    # taxon_to_oscode.py
    print(taxon)
    while taxon in MADEUP_SPECIES and taxon != "LUCA":
        # print(taxon)
        # Get parent of taxon - handy BioPython trick
        taxon_clade = find_taxon_clade(taxon, tree.clade)
        node_path = tree.get_path(taxon_clade)
        if len(node_path) > 1:
            parent_clade = node_path[-2]
        else:
            parent_clade = tree.clade
        taxon = parent_clade.name

    # Remove after getting LUCA's real values - assuming most everything is cool with LUCA
    if taxon == "LUCA":
        # virus stuff
        if term in ("GO:0019012", "GO:0039679", "GO:0044423"):
            return False
        else:
            return True

    try:
        result = term_constraint_lists[term][taxon_indexes[taxon]]
    except IndexError:
        print(taxon)
        result = term_constraint_lists[term][taxon_indexes[taxon]]
    if result == '0':
        return False
    return True

def append_madeup_species_to_table():
    # List hyphenated species
    # Reconstruct entire table file
    # with open("new_table_file", "w+") as nf:
    with open(args.output_file, "w+") as nf:
        writer = csv.writer(nf, delimiter="\t")
        header = ["GOterm"]
        out_rows = []
        out_term_values = {}
        for tk in list(taxon_indexes.keys()) + MADEUP_SPECIES:
            header.append(tk)
            for term in term_constraint_lists:
                if validate_taxon_term(tk, term):
                    result = 1
                else:
                    result = 0
                if term in out_term_values:
                    out_term_values[term].append(result)
                else:
                    out_term_values[term] = [term, result]

        writer.writerow(header)
        for otv in out_term_values:
            if len(slim_terms) == 0 or otv in slim_terms:
                writer.writerow(out_term_values[otv])

if __name__ == "__main__":
    append_madeup_species_to_table()