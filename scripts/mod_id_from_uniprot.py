import argparse
import csv
from pthr_db_caller.models import refprot_file


parser = argparse.ArgumentParser()
parser.add_argument('-u', '--uniprot_ids')
parser.add_argument('-i', '--idmapping_file')
parser.add_argument('-m', '--mod_prefix')


# python3 scripts/mod_id_from_uniprot.py -u unmapped_mod_uniprots.txt -i resources/UP000001940_6239.idmapping -m WormBase > mod_ids_from_uniprot.tsv
if __name__ == "__main__":
    args = parser.parse_args()

    uniprot_ids = []
    with open(args.uniprot_ids) as uf:
        for l in uf.readlines():
            l = l.rstrip()
            if l == "uniprot_id":
                # Column name - skip
                continue
            uniprot_ids.append(l)

    idmappings: refprot_file.RefProtIdmappingFile = refprot_file.RefProtIdmappingFile.parse(args.idmapping_file)

    source_type = args.mod_prefix
    for u in uniprot_ids:
        mod_id = None
        if u not in idmappings.by_uniprot:
            print("No ID mappings for {}".format(u))
            continue
        for m_entry in idmappings.by_uniprot[u]:
            if m_entry.source_type == source_type:
                mod_id = m_entry.gene_id
                break
        if mod_id:
            print("\t".join([u, mod_id]))
        else:
            pass
            # print("No {} ID mapping for {}".format(source_type, u))
