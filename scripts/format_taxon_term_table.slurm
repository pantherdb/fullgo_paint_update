#!/bin/bash
#SBATCH --time=1-00:00:00
#SBATCH --ntasks=1
#SBATCH --mem=96gb
#SBATCH --account=lc_pdt
#SBATCH --partition=thomas
#SBATCH --mail-type=END,FAIL

. env/bin/activate

./gaferencer-0.4.1/bin/gaferencer -J-Xmx96G taxa --contexts resources/go_context.jsonld --ontfile true $BASE_PATH/go-plus.owl resources/paint_taxons_15.txt $BASE_PATH/new_table_file
python3 scripts/taxon_to_oscode.py -t $BASE_PATH/new_table_file -s resources/paint_taxons_15.txt -r resources/RefProt_README_15 -o $BASE_PATH/taxon_term_table_converted
python3 scripts/taxon_validate.py -t $BASE_PATH/taxon_term_table_converted -p $BASE_PATH/species_pthr15_annot.nhx -o $BASE_PATH/TaxonConstraintsLookup.txt
