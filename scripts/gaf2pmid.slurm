#!/bin/tcsh
#SBATCH --time=16:00:00
#SBATCH --ntasks=1
#SBATCH --mem=96gb
#SBATCH --account=lc_pdt
#SBATCH --partition=thomas
#SBATCH --mail-type=END,FAIL

source /home/pmd-02/pdt/pdthomas/panther/cshrc.panther

perl scripts/gaf2pmid.pl -g $FULL_GAF_FILES_PATH/ > $FULL_BASE_PATH/gaf2pmid_results