#!/bin/bash
#SBATCH --time=01:00:00
#SBATCH --ntasks=1
#SBATCH --mem=96gb
#SBATCH --account=$HPC_ACCOUNT
#SBATCH --partition=thomas
#SBATCH --mail-type=END,FAIL

module load openjdk

bin/robot export --input $BASE_PATH/go.obo --format tsv --header "ID|hasOBONamespace" --export $BASE_PATH/resources/go_aspects.tsv
awk '$$2 != ""' $BASE_PATH/resources/go_aspects.tsv | tail -n +2 > $BASE_PATH/resources/go_aspects.tsv.tmp
mv $BASE_PATH/resources/go_aspects.tsv.tmp $BASE_PATH/resources/go_aspects.tsv