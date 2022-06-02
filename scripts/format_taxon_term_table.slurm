#!/bin/bash
#SBATCH --time=6:00:00
#SBATCH --ntasks=1
#SBATCH --mem=160gb
#SBATCH --mail-type=END,FAIL

module load gcc/8.3.0
module load python/3.6.8
module load openjdk
. env/bin/activate

robot query -i $BASE_PATH/go-gaf.owl --update scripts/sparql/ancestral-species.rq -o $BASE_PATH/go-gaf-anc-desc.ofn

./gaferencer-0.5/bin/gaferencer -J-Xmx150G taxa --contexts resources/anc_context.json --ontfile true --ontology-iri $BASE_PATH/go-gaf-anc-desc.ofn --taxon-list resources/paint_taxons.txt --taxon-table $BASE_PATH/new_table_file

align_taxon_term_table_species.py -t $BASE_PATH/new_table_file -o $ORGANISM_DAT -p $BASE_PATH/species_pthr_annot.nhx -f $BASE_PATH/TaxonConstraintsLookup.txt.tmp

grep -e "^GO" $BASE_PATH/TaxonConstraintsLookup.txt.tmp > $BASE_PATH/TaxonConstraintsLookup.txt
