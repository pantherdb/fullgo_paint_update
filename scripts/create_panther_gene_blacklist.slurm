#!/bin/bash
#SBATCH --time=3:00:00
#SBATCH --ntasks=1
#SBATCH --mem=96gb
#SBATCH --account=$HPC_ACCOUNT
#SBATCH --partition=thomas
#SBATCH --mail-type=END,FAIL

cut -f1 $GENE_PATH | rev | cut -d "=" -f1 | rev > $R_DIR/pthr_uniprot_ids
comm -13 <(sort $R_DIR/uniprot_protein.gpi.ids) <(sort $R_DIR/pthr_uniprot_ids) > $R_DIR/panther_blacklist.txt