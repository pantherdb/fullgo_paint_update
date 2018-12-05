#!/bin/tcsh
#SBATCH --time=16:00:00
#SBATCH --ntasks=1
#SBATCH --mem=96gb
#SBATCH --account=lc_pdt
#SBATCH --partition=thomas

source /home/pmd-02/pdt/pdthomas/panther/cshrc.panther

perl scripts/FindAllParents.pl $FULL_BASE_PATH/goparentchild.tsv $FULL_BASE_PATH/AllParentsofGOTerms.txt
perl scripts/printHierarchy.pl $FULL_BASE_PATH/AllParentsofGOTerms.txt $FULL_BASE_PATH/FinalChildParent-Hierarchy.dat
perl scripts/hierarchyfinalstep.pl $FULL_BASE_PATH
perl $PWD/scripts/hierarchyfinalstep.pl $FULL_BASE_PATH