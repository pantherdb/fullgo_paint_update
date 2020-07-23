#!/bin/tcsh

source /home/pmd-02/pdt/pdthomas/panther/cshrc.panther

perl $PWD/scripts/fullGoMappingPthrHierarchy.pl \
-f $FULL_GAF_FILES_PATH/group_$SLURM_PROCID/ \
-t $PWD/$TAXON_ID_PATH \
-i $IDENTIFIER_PATH \
-g $GENE_PATH \
-o $FULL_BASE_PATH/go.obo \
-w $FULL_BASE_PATH/Pthr_GO_$PANTHER_VERSION.tsv.$SLURM_PROCID \
-e $FULL_BASE_PATH/PthrGOLog_$PANTHER_VERSION.txt.$SLURM_PROCID \
-d $FULL_BASE_PATH/ \
-H $PANTHER_VERSION.dat.$SLURM_PROCID