#!/bin/tcsh
#SBATCH --time=08:00:00
#SBATCH --ntasks=1
#SBATCH --mem=48gb

source /home/pmd-02/pdt/pdthomas/panther/cshrc.panther

perl /auto/rcf-proj3/hm/debert/external/scripts/fullGoMappingPthr.pl -f /auto/rcf-proj3/hm/debert/external/fullgo/gaf_files/ -t /auto/rcf-proj3/hm/debert/external/scripts/pthr13_code_taxId.txt -i /auto/pmd-02/pdt/pdthomas/panther/xiaosonh/UPL/PANTHER13.1/library_building/DBload/identifier.dat -g /auto/pmd-02/pdt/pdthomas/panther/xiaosonh/UPL/PANTHER13.1/library_building/DBload/gene.dat -o /auto/rcf-proj3/hm/debert/external/fullgo/go.obo -w /auto/rcf-proj3/hm/debert/external/fullgo/Pthr_GO.tsv -e /auto/rcf-proj3/hm/debert/external/fullgo/PthrGOLog.txt
