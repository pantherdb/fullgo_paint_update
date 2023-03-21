#!/bin/bash
#SBATCH --time=01:00:00
#SBATCH --ntasks=1
#SBATCH --mem=96gb
#SBATCH --account=$HPC_ACCOUNT
#SBATCH --partition=thomas
#SBATCH --mail-type=END,FAIL

module load gcc/8.3.0
module load openjdk

bin/robot extract --method MIREOT --input $BASE_PATH/go.obo --branch-from-term GO:0032991 export --format tsv --header "ID" --export $BASE_PATH/resources/complex_terms.tsv
