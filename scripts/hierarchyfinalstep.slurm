#!/bin/tcsh
#SBATCH --time=24:00:00
#SBATCH --ntasks=1
#SBATCH --mem=96gb
#SBATCH --account=lc_pdt
#SBATCH --partition=thomas
#SBATCH --mail-type=END,FAIL

perl scripts/FindAllParents.pl $BASE_PATH/goparentchild.tsv $BASE_PATH/AllParentsofGOTerms.txt
perl scripts/printHierarchy.pl $BASE_PATH/AllParentsofGOTerms.txt $BASE_PATH/FinalChildParent-Hierarchy.dat
perl scripts/hierarchyfinalstep.pl $BASE_PATH -m Pthr_GO_$PANTHER_VERSION.tsv -v $PANTHER_VERSION
