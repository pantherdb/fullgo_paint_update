import argparse
import csv

# E.g. python3 scripts/add_pc_to_constraints.py -t TaxonConstraintsLookup14Slim.txt -p resources/pc_terms -o TaxonConstraintsLookup14SlimPlusPC.txt
parser = argparse.ArgumentParser()
parser.add_argument('-t', '--constraints_file')
parser.add_argument('-p', '--pc_terms_file')
parser.add_argument('-o', '--outfile')

args = parser.parse_args()

pc_terms = []
with open(args.pc_terms_file) as pcf:
    for pc in pcf.readlines():
        pc_terms.append(pc.rstrip())

outfile = open(args.outfile, 'w+')
writer = csv.writer(outfile, delimiter='\t')
with open(args.constraints_file) as tcf:
    reader = csv.reader(tcf, delimiter='\t')
    for r in reader:
        writer.writerow(r)
    col_count = len(r)
    for pc in pc_terms:
        row = [pc] + ["1"]*(col_count - 1)
        writer.writerow(row)

outfile.close()