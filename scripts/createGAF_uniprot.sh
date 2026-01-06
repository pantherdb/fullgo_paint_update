#!/bin/bash

( perl scripts/createGAF.pl -i $GAF_PROFILE \
-n $NODE_PATH \
-N $TREE_NODES_DIR \
-a $BASE_PATH/resources/$ANNOT \
-q $BASE_PATH/resources/$ANNOT_QUALIFIER \
-g $BASE_PATH/resources/$GO_AGG \
-t $TAIR_MAP \
-u $ARAPORT_MAP \
-c $BASE_PATH/resources/$EVIDENCE \
-P $BASE_PATH/resources/paint_exp_aggregate \
-T $BASE_PATH/resources/$TAXON \
-G $GENE_PATH \
-p $BASE_PATH/resources/zfin.gpi,$BASE_PATH/resources/japonicusdb.gpi \
-s $GAF_VERSION \
-C $BASE_PATH/resources/complex_terms.tsv \
-r $BASE_PATH/goparentchild_isaonly.tsv \
-o $IBA_DIR -U > $BASE_PATH/IBD_uniprot ) 2> $BASE_PATH/createGAF_uniprot.err

# perl scripts/fix_pombe_symbol.pl -i $IBA_DIR/gene_association.paint_pombase.gaf -p $BASE_PATH/resources/gene_IDs_names.tsv -d $BASE_PATH/resources/sysID2product.tsv > $BASE_PATH/gene_association.paint_pombase.fixed.gaf
# cp -f $BASE_PATH/gene_association.paint_pombase.fixed.gaf $IBA_DIR/gene_association.paint_pombase.gaf