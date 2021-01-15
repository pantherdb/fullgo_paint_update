#!/bin/bash
#SBATCH --time=1-00:00:00
#SBATCH --ntasks=1
#SBATCH --mem=96gb
#SBATCH --account=$HPC_ACCOUNT
#SBATCH --partition=thomas
#SBATCH --mail-type=END,FAIL

. env/bin/activate

./gaferencer-0.4.1/bin/gaferencer -J-Xmx96G taxa --contexts resources/go_context.jsonld --ontfile true $BASE_PATH/go-plus.owl resources/paint_taxons_15.txt $BASE_PATH/new_table_file

align_taxon_term_table_species.py -t $BASE_PATH/new_table_file -o $ORGANISM_DAT -p $BASE_PATH/species_pthr15_annot.nhx -f $BASE_PATH/TaxonConstraintsLookup.txt
