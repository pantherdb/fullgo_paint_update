#!/bin/bash
#SBATCH --time=3:00:00
#SBATCH --ntasks=1
#SBATCH --mem=96gb
#SBATCH --account=$HPC_ACCOUNT
#SBATCH --partition=thomas
#SBATCH --mail-type=END,FAIL

gunzip $R_DIR/uniprot_protein.gpi.gz
cut -f2 $R_DIR/uniprot_protein.gpi > $R_DIR/uniprot_protein.gpi.ids