#!/bin/bash
#SBATCH --time=1-00:00:00
#SBATCH --ntasks=1
#SBATCH --mem=96gb
#SBATCH --account=$HPC_ACCOUNT
#SBATCH --partition=thomas
#SBATCH --mail-type=END,FAIL

module load gcc/8.3.0
module load python/3.6.8
. env/bin/activate

format_xml_iba_to_gaf.py -f $IBA_XML_DIR \
-g $BASE_PATH/resources/go_aspects.tsv \
-c $BASE_PATH/resources/complex_terms.tsv \
-s resources/paint_iba_files.tsv \
-d $IBA_DIR \
-a GAF \
-p $PANTHER_VERSION \
-r $GO_RELEASE_DATE \
-u $BASE_PATH/resources/panther_blacklist.txt \
-b $BASE_PATH/IBD

perl scripts/fix_pombe_symbol.pl -i $IBA_DIR/gene_association.paint_pombase.gaf -p $BASE_PATH/resources/allNames.tsv -d $BASE_PATH/resources/sysID2product.tsv > $BASE_PATH/gene_association.paint_pombase.fixed.gaf
cp -f $BASE_PATH/gene_association.paint_pombase.fixed.gaf $IBA_DIR/gene_association.paint_pombase.gaf