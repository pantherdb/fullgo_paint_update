#!/bin/tcsh
#SBATCH --time=16:00:00
#SBATCH --ntasks=1
#SBATCH --mem=96gb
#SBATCH --account=lc_pdt
#SBATCH --partition=thomas
#SBATCH --mail-type=END,FAIL

source /home/pmd-02/pdt/pdthomas/panther/cshrc.panther

perl $PWD/scripts/fullGoMappingPthrHierarchy.pl \
-f $FULL_GAF_FILES_PATH/ \
-t $PWD/$TAXON_ID_PATH \
-i $IDENTIFIER_PATH \
-g $GENE_PATH \
-o $FULL_BASE_PATH/go.obo \
-w $FULL_BASE_PATH/Pthr_GO_$PANTHER_VERSION.tsv \
-e $FULL_BASE_PATH/PthrGOLog_$PANTHER_VERSION.txt \
-d $FULL_BASE_PATH/ \
-P $PANTHER_VERSION