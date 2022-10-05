#!/bin/tcsh
#SBATCH --time=24:00:00
#SBATCH --ntasks=1
#SBATCH --mem=96gb
#SBATCH --account=$HPC_ACCOUNT
#SBATCH --partition=thomas
#SBATCH --mail-type=END,FAIL

( perl scripts/createGAF.pl -i $GAF_PROFILE \
-n $NODE_PATH \
-N $TREE_NODES_DIR \
-a $BASE_PATH/resources/$ANNOT \
-q $BASE_PATH/resources/$ANNOT_QUALIFIER \
-g $BASE_PATH/resources/$GO_AGG \
-t $TAIR_MAP \
-u $ARAPORT_MAP \
-c $BASE_PATH/resources/$EVIDENCE \
-T $BASE_PATH/resources/$TAXON \
-G $GENE_PATH \
-b $BASE_PATH/resources/panther_blacklist.txt \
-s $GAF_VERSION \
-C $BASE_PATH/resources/complex_terms.tsv \
-r $BASE_PATH/goparentchild_isaonly.tsv \
-o $IBA_DIR > $BASE_PATH/IBD ) > $BASE_PATH/err

perl scripts/fix_pombe_symbol.pl -i $IBA_DIR/gene_association.paint_pombase.gaf -p $BASE_PATH/resources/gene_IDs_names.tsv -d $BASE_PATH/resources/sysID2product.tsv > $BASE_PATH/gene_association.paint_pombase.fixed.gaf
cp -f $BASE_PATH/gene_association.paint_pombase.fixed.gaf $IBA_DIR/gene_association.paint_pombase.gaf