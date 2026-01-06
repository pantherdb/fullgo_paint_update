import argparse
import csv
from datetime import datetime

from pthr_db_caller import mod_id_mapper
from pthr_db_caller.models import panther
from oaklib import get_adapter
from typing import List


parser = argparse.ArgumentParser()
parser.add_argument('-e', '--paint_exp_tsv', help="DB query results TSV")
parser.add_argument('-o', '--ontology_file', required=True, help="Ontology file to fetch GO term aspects")
parser.add_argument('-g', '--gene_dat', required=True, help="Gene.dat file to fetch gene symbols, names and synonyms")
parser.add_argument('-i', '--gpi_files', nargs='*', help="gpi uniprot mappings to use")
parser.add_argument('-r', '--tair_mapping_file', help="TAIR mapping file")
parser.add_argument('-u', '--araport_to_uniprot_file')
parser.add_argument('-s', '--organism_dat', help="Organism.dat file for fetching taxon given OS code")
parser.add_argument('-U', '--goa_mode', action='store_const', const=True, help="Output primary IDs as UniProt")


class GafFactory:
    def __init__(self, ontology_file, gene_dat, gpi_files: List, tair_file, araport_file, organism_dat, goa_mode=None):
        # Ontology to fetch GO term aspects
        self.oak_adapter = get_adapter(ontology_file)
        self.aspect_lkp = {}
        # State rules for determining the relation given aspect of a GO term or if it's a complex
        self.relation_rules = {
            "P": "involved_in",
            "F": "enables",
            "C": "is_active_in",
            "complex": "part_of"
        }
        # Gene.dat to fetch gene symbols, names and synonyms
        self.gene_dat = panther.GeneDatFile.parse(gene_dat)
        self.gene_entry_lkp = {g.long_id.uniprot_id: g for g in self.gene_dat}
        self.id_mapper = mod_id_mapper.MODIDMapper.from_files(
            gpi_uniprot_files=gpi_files,
            tair_mapping_file=tair_file,
            araport_mapping_file=araport_file
        )
        self.oscode_to_taxon_lkp = self.parse_organism_dat(organism_dat)
        self.goa_mode = goa_mode

    @staticmethod
    def parse_organism_dat(organism_dat):
        oscode_to_taxon_lkp = {}
        with open(organism_dat) as f:
            reader = csv.reader(f, delimiter='\t')
            for row in reader:
                if len(row) < 2:
                    continue
                os_code = row[2]
                taxon_id = row[5]
                oscode_to_taxon_lkp[os_code] = taxon_id
        return oscode_to_taxon_lkp

    def get_term_aspect(self, term_id) -> str:
        """Fetch the aspect of a GO term using the ontology adapter."""
        try:
            if term_id in self.aspect_lkp:
                return self.aspect_lkp[term_id]
            term = self.oak_adapter.node(term_id)
            if term is None:
                return ''
            aspect = None
            for prop in term.meta.basicPropertyValues:
                if 'hasOBONamespace' in prop.pred:
                    namespace = prop.val
                    if namespace == 'biological_process':
                        aspect = 'P'
                    elif namespace == 'molecular_function':
                        aspect = 'F'
                    elif namespace == 'cellular_component':
                        aspect = 'C'
                    if aspect:
                        self.aspect_lkp[term_id] = aspect
                        return self.aspect_lkp[term_id]
            return ''
        except Exception as e:
            print(f"Error fetching aspect for term {term_id}: {e}")
            return ''

    def is_complex(self, go_id) -> bool:
        """Check if a GO term is a complex by seeing if it's a descendant of GO:0032991"""
        try:
            # Check if the term is a descendant of GO:0032991 (macromolecular complex)
            ancestors = self.oak_adapter.ancestors(go_id, predicates=['i'], reflexive=True)
            if 'GO:0032991' in ancestors:
                return True
            return False
        except Exception as e:
            print(f"Error checking if term {go_id} is a complex: {e}")
            return False


    def tsv_row_to_gaf(self, row):
        long_id = row['primary_ext_acc']
        uniprot_id = long_id.split('=')[-1]
        gene_entry = self.gene_entry_lkp.get(uniprot_id)
        mod_id = self.id_mapper.get_short_id(long_id)
        if self.goa_mode:
            db = "UniProtKB"
            db_object_id = uniprot_id
        else:
            db = mod_id.split(':')[0] if ':' in mod_id else ''
            db_object_id = mod_id.split(':', maxsplit=1)[1]
        db_object_symbol = gene_entry.synonym
        go_id = row['accession']
        aspect = self.get_term_aspect(go_id)
        default_relation = self.relation_rules[aspect]
        if aspect == "C" and self.is_complex(go_id):
            default_relation = self.relation_rules["complex"]
        qualifier = row['qualifier'] if row['qualifier'] else None
        if qualifier and qualifier != 'NOT':
            relations = qualifier.lower()
        elif qualifier == 'NOT':
            relations = 'NOT|' + default_relation
        else:
            relations = default_relation

        db_reference = row['reference']
        evidence_code = row['confidence_code']
        with_from = ''

        db_object_name = gene_entry.description
        db_object_synonym = gene_entry.synonym
        db_object_type = 'protein'
        os_code = long_id.split("|")[0]
        taxon = 'taxon:' + self.oscode_to_taxon_lkp.get(os_code)
        date = row['creation_date'].replace('-', '')  # YYYYMMDD
        assigned_by = 'GO_Central'
        annotation_extension = ''
        gene_product_form_id = ''
        return '\t'.join([
            db, db_object_id, db_object_symbol, relations, go_id, db_reference,
            evidence_code, with_from, aspect, db_object_name, db_object_synonym,
            db_object_type, taxon, date, assigned_by, annotation_extension, gene_product_form_id
        ])


if __name__ == '__main__':
    args = parser.parse_args()

    gaf_factory = GafFactory(
        ontology_file=args.ontology_file,
        gene_dat=args.gene_dat,
        gpi_files=args.gpi_files,
        tair_file=args.tair_mapping_file,
        araport_file=args.araport_to_uniprot_file,
        organism_dat=args.organism_dat,
        goa_mode=args.goa_mode
    )

    gaf_version = "2.2"
    todays_date = datetime.today().strftime('%Y-%m-%d')
    panther_version = "19.0"
    go_version = "2025-07-22"
    headers = [
    f"!gaf-version: {gaf_version}",
    f"!Created on {todays_date}",
    "!generated-by: PANTHER",
    f"!date-generated: {todays_date}",
    f"!PANTHER version: {panther_version}.",
    f"!GO version: {go_version}."
    ]
    print("\n".join(headers))

    with open(args.paint_exp_tsv, newline='') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            gaf_line = gaf_factory.tsv_row_to_gaf(row)
            print(gaf_line)
