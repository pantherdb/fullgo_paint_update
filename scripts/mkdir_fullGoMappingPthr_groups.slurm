#!/bin/bash
#SBATCH --time=16:00:00
#SBATCH --ntasks=1
#SBATCH --mem=96gb
#SBATCH --account=lc_pdt
#SBATCH --partition=thomas
#SBATCH --mail-type=END,FAIL

srun scripts/mkdir_fullGoMappingPthr_groups.sh $GAF_FILES_PATH