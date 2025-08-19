#!/usr/bin/env python3
"""
Script to replace UniProt IDs with EcoCyc IDs in GAF file using GPI lookup.
Usage: python replace_ids.py input.gaf ecocyc.gpi output.gaf
"""

import sys
import argparse
import re
from typing import Dict


parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input_gaf", help="Path to the input GAF file")
parser.add_argument("-g", "--gpi_file", help="Path to the GPI file containing UniProt")


def parse_gpi_file(gpi_file: str) -> Dict[str, str]:
    """
    Parse GPI file to create UniProt ID -> EcoCyc ID mapping.
    
    Args:
        gpi_file: Path to the GPI file
    
    Returns:
        Dictionary mapping UniProt IDs to EcoCyc IDs
    """
    mapping = {}
    
    with open(gpi_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comment lines
            if line.startswith('!') or not line:
                continue
            
            fields = line.split('\t')
            if len(fields) >= 8:
                ecocyc_id = fields[0]  # Column 1: EcoCyc ID
                xref_list = fields[9] if len(fields) > 9 else ""  # Column 10: Cross-references
                
                # Extract UniProt ID from cross-references
                uniprot_match = re.search(r'UniProtKB:([A-Z0-9]+)', xref_list)
                if uniprot_match:
                    uniprot_id = uniprot_match.group(1)
                    mapping[ecocyc_id] = uniprot_id
    
    return mapping

def process_gaf_file(input_gaf: str, id_mapping: Dict[str, str]):
    """
    Process GAF file and replace UniProt IDs with EcoCyc IDs.
    
    Args:
        input_gaf: Path to input GAF file
        id_mapping: Dictionary mapping UniProt IDs to EcoCyc IDs
    """
    with open(input_gaf, 'r') as infile:
        for line in infile:
            line = line.strip()
            
            # Skip comment lines and empty lines
            if line.startswith('!') or not line:
                print(line)
                # outfile.write(line + '\n')
                continue
            
            fields = line.split('\t')
            
            # GAF format has 15+ columns
            if len(fields) >= 15:
                db_object_id = f"{fields[0]}:{fields[1]}"  # Column 2: DB Object ID

                if db_object_id in id_mapping:
                    uniprot_id = id_mapping[db_object_id]
                    # Swap primary ID
                    fields[0] = "UniProtKB"
                    fields[1] = uniprot_id
            
            print("\t".join(fields))
            # outfile.write('\t'.join(fields) + '\n')

if __name__ == "__main__":
    args = parser.parse_args()

    input_gaf = args.input_gaf
    gpi_file = args.gpi_file
    # output_gaf = sys.argv[3]
    
    id_mapping = parse_gpi_file(gpi_file)
    
    process_gaf_file(input_gaf, id_mapping)
