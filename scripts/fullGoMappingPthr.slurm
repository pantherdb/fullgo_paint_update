#!/bin/tcsh
#SBATCH --time=08:00:00
#SBATCH --ntasks=1
#SBATCH --mem=48gb

source /home/pmd-02/pdt/pdthomas/panther/cshrc.panther

perl $PWD/scripts/fullGoMappingPthr.pl \
-f $FULL_GAF_FILES_PATH/ \
-t $PWD/scripts/pthr13_code_taxId.txt \
-i /auto/pmd-02/pdt/pdthomas/panther/xiaosonh/UPL/PANTHER13.1/library_building/DBload/identifier.dat \
-g /auto/pmd-02/pdt/pdthomas/panther/xiaosonh/UPL/PANTHER13.1/library_building/DBload/gene.dat \
-o $FULL_BASE_PATH/go.obo \
-w $FULL_BASE_PATH/Pthr_GO.tsv \
-e $FULL_BASE_PATH/PthrGOLog.txt
