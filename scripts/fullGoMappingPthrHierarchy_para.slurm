#!/bin/tcsh
#SBATCH --time=16:00:00
#SBATCH --nodes=$NUMGROUPS
#SBATCH --ntasks-per-node=1
#SBATCH --mem=96gb
#SBATCH --account=lc_pdt
#SBATCH --partition=thomas
#SBATCH --mail-type=END,FAIL

setenv PWD $PWD
setenv FULL_GAF_FILES_PATH $FULL_GAF_FILES_PATH
setenv TAXON_ID_PATH $TAXON_ID_PATH
setenv IDENTIFIER_PATH $IDENTIFIER_PATH
setenv GENE_PATH $GENE_PATH
setenv FULL_BASE_PATH $FULL_BASE_PATH
setenv PANTHER_VERSION $PANTHER_VERSION

srun scripts/fullGoMappingPthrHierarchy_para.csh