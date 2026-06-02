import argparse
import csv
import re
import sys
from datetime import datetime

from pthr_db_caller.mod_id_mapper import MODIDMapper
from pthr_db_caller.models import panther
from oaklib import get_adapter
from typing import List, Optional, Tuple


parser = argparse.ArgumentParser()
parser.add_argument('-e', '--paint_exp_tsv', help="DB query results TSV")
parser.add_argument('-o', '--ontology_file', required=True, help="Ontology file to fetch GO term aspects")
parser.add_argument('-g', '--gene_dat', required=True, help="Gene.dat file to fetch gene symbols, names and synonyms")
parser.add_argument('-i', '--gpi_files', nargs='*', help="gpi uniprot mappings to use")
parser.add_argument('-r', '--agi_lookup_file', required=True,
                    help="AGI_LocusCode lookup TSV (e.g. resources/AGI_LocusCode_UniProt_19.gene2acc)")
parser.add_argument('-s', '--organism_dat', help="Organism.dat file for fetching taxon given OS code")
parser.add_argument('-p', '--profile', required=True,
                    help="profile.txt path to read PANTHER and GO versions from")
parser.add_argument('-U', '--goa_mode', action='store_const', const=True, help="Output primary IDs as UniProt")


def parse_profile(profile_path: str) -> Tuple[str, str]:
    """Read PANTHER and GO versions from a profile.txt TSV.

    Lines are tab-separated `key\\tvalue`; PANTHER values carry a `v.` prefix
    that is stripped here.
    """
    panther_version = None
    go_version = None
    with open(profile_path) as f:
        for line in f:
            parts = line.rstrip('\n').split('\t')
            if len(parts) < 2:
                continue
            key, value = parts[0], parts[1]
            if key == 'PANTHER':
                panther_version = value[2:] if value.startswith('v.') else value
            elif key == 'GO':
                go_version = value
    if not panther_version or not go_version:
        raise ValueError(
            f"profile.txt at {profile_path} is missing PANTHER or GO row"
        )
    return panther_version, go_version


class AGIMODIDMapper(MODIDMapper):
    """MODIDMapper variant that resolves ARATH long_ids to AGI_LocusCode:ATxGNNNNN
    via a single 3-column TSV (source_id, uniprot_id, canonical_agi). UniProt match
    is preferred over the gene-id match. Handles the TAIR:locus:NNN form that the
    parent class otherwise leaves untouched."""

    def __init__(self, agi_by_protein=None, agi_by_geneid=None, **kwargs):
        super().__init__(**kwargs)
        self.agi_by_protein = agi_by_protein or {}
        self.agi_by_geneid = agi_by_geneid or {}

    @classmethod
    def from_files(cls, gpi_uniprot_files: List[str] = None, agi_lookup_file: str = None):
        gpi_uniprot_mappings = cls.parse_gpi_uniprot_file(gpi_uniprot_files or [])
        agi_by_protein, agi_by_geneid = cls.parse_agi_lookup_file(agi_lookup_file)
        return cls(
            gpi_uniprot_mappings=gpi_uniprot_mappings,
            agi_by_protein=agi_by_protein,
            agi_by_geneid=agi_by_geneid,
        )

    @staticmethod
    def parse_agi_lookup_file(path: str) -> Tuple[dict, dict]:
        by_protein, by_geneid = {}, {}
        with open(path) as f:
            for line in f:
                line = line.rstrip('\n')
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) < 3:
                    continue
                source_id, protein_id, canonical_agi = parts[0], parts[1], parts[2]
                if not canonical_agi:
                    continue
                if protein_id:
                    by_protein[protein_id] = canonical_agi
                if source_id:
                    bare = re.sub(r'^\w+:', '', source_id)
                    by_geneid[bare.upper()] = canonical_agi
        return by_protein, by_geneid

    def lookup_agi(self, gene_id: str, protein_id: str) -> Optional[str]:
        bare_protein = re.sub(r'^\w+:', '', protein_id or '')
        bare_gene = re.sub(r'^\w+:', '', gene_id or '')
        if bare_protein and bare_protein in self.agi_by_protein:
            return self.agi_by_protein[bare_protein]
        if bare_gene and bare_gene.upper() in self.agi_by_geneid:
            return self.agi_by_geneid[bare_gene.upper()]
        return None

    def get_short_id(self, long_id: str) -> Optional[str]:
        try:
            org, gene_id, protein_id = self.parse_long_id(long_id)
        except ValueError as e:
            print(f"Error parsing ID: {e}", file=sys.stderr)
            return None

        if gene_id.startswith('TAIR') or gene_id.startswith('Araport'):
            short_id = self.lookup_agi(gene_id, protein_id)
            if short_id is None:
                print(f"ARATH leaf has no mapped AGI_LocusCode (longId={long_id}).", file=sys.stderr)
                return None
            self.id_lookup[long_id] = short_id
            return short_id

        return super().get_short_id(long_id)


class GafFactory:
    def __init__(self, ontology_file, gene_dat, gpi_files: List, agi_lookup_file, organism_dat, goa_mode=None):
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
        self.id_mapper = AGIMODIDMapper.from_files(
            gpi_uniprot_files=gpi_files,
            agi_lookup_file=agi_lookup_file,
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
        agi_lookup_file=args.agi_lookup_file,
        organism_dat=args.organism_dat,
        goa_mode=args.goa_mode
    )

    gaf_version = "2.2"
    todays_date = datetime.today().strftime('%Y-%m-%d')
    panther_version, go_version = parse_profile(args.profile)
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
