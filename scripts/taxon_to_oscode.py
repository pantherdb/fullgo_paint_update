import csv
import subprocess
import os
from ontobio.sparql.sparql_ontol_utils import run_sparql

query = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?o FROM <http://purl.obolibrary.org/obo/merged/NCBITAXON> WHERE {{
    <http://purl.obolibrary.org/obo/NCBITaxon_{}> rdfs:label ?o
}}
"""

# Command-ify this script to separate slurm from no-slurm (internet-required)

# Download or locate RefProt readme

# Get all taxonID-to-OSCode mappings from ref prot
with open("resources/README") as rf:
    taxon_to_os = {}
    oscodes = []
    for l in rf.readlines():
        if l.startswith("UP"):
            l_bits = l.split(" ")
            l_bits = list(filter(None, l_bits))
            if len(l_bits) > 3 and l_bits[2] != 'None' and len(l_bits[2]) == 5:
                # if l_bits[1] == "99287":
                taxon_to_os["NCBITaxon:{}".format(l_bits[1])] = l_bits[2]
                oscodes.append(l_bits[2])

# query or locate list of paint_taxons - pretty much the taxons passed into gaferencer

# Get list of taxon IDs used to generate taxon_term_table
with open("resources/paint_taxons.txt") as pf:
    taxons_to_convert = []
    for l in pf.readlines():
        taxon_id = l.rstrip()
        taxons_to_convert.append(taxon_id)
        if taxon_id not in taxon_to_os:
            # print(taxon_id)
            thing = run_sparql(query.format(taxon_id.split(":")[1]))
            # print(thing)
            taxon_name = ""
            if len(thing) > 0:
                taxon_name = thing[0]['o']['value']
                # print(taxon_name)
                taxon_to_os[taxon_id] = taxon_name
                if taxon_name == "Bacillus <bacterium>":
                    taxon_to_os[taxon_id] = "Bacillus"
            if taxon_id == "NCBITaxon:85003":
                # 85003 reassigned to 1760 for Actinobacteria
                taxon_to_os[taxon_id] = "Actinobacteria"

# Locate

# Get OS codes existing in current TaxonConstraintsLookup.txt PAINT file - check if there are any mappings missing
with open("resources/taxon_constraints_taxons.tsv") as ctf:
    required_taxons = []
    for l in ctf.readlines():
        if len(l.rstrip()) == 5:
            required_taxons.append(l.rstrip())
            if l.rstrip() not in oscodes:
                print("{} not found in README".format(l.rstrip()))
                # ASPFM not found in README # Should be ASPFU?
                # BRAJA not found in README # bradyrhizobium - Don't support in 13.1 or 14 - changed to BRADU
                # CANFA not found in README # dog - Don't support in 13.1 or 14 - changed to CANLF
                # PYRKO not found in README # pyrococcus - Don't support in 13.1 or 14

# Write out taxonID-to-OSCode mappings to tsv
with open("taxon_to_oscode.tsv", "w+") as outf:
    writer = csv.writer(outf, delimiter="\t")
    for t in taxons_to_convert:
        try:
            writer.writerow([t, taxon_to_os[t]])
        except:
            print("OS code missing for {}".format(t))

with open("taxon_term_table") as t3f:
    # Fix header of taxon_term_table
    # table_header = subprocess.getoutput("head -n 1 taxon_term_table")
    table_lines = t3f.readlines()
    table_header = table_lines[0].rstrip()
    headers = table_header.split("\t")
    new_headers = []
    for h in headers:
        new_header = h
        if h.startswith("NCBITaxon:") and h in taxon_to_os:
            new_header = taxon_to_os[h]
        print(new_header)
        new_headers.append(new_header)
    table_lines[0] = "{}\n".format("\t".join(new_headers))
    # os.system("sed -i \"1s/.*/{}/\" taxon_term_table".format("\t".join(new_headers))) # Mac and Linux sed cmds are incompatible

t3c = open("taxon_term_table_converted", "w+")
t3c.writelines(table_lines)
t3c.close()


# print(table_header)
# with open("taxon_term_table_plus")