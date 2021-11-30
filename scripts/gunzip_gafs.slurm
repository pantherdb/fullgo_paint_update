#!/bin/tcsh
#SBATCH --time=3:00:00
#SBATCH --ntasks=1
#SBATCH --mem=96gb
#SBATCH --account=$HPC_ACCOUNT
#SBATCH --partition=thomas
#SBATCH --mail-type=END,FAIL

gunzip $GAF_FILES_PATH/*.gz
