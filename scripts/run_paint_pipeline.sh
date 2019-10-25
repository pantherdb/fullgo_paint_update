START_TIME=$SECONDS

BASE_PATH=$(date +%Y-%m-%d)_fullgo_test
mkdir -p $BASE_PATH
rm $BASE_PATH/log.txt
touch $BASE_PATH/log.txt

make BASE_PATH=$BASE_PATH load_raw_go_to_paint | tee -a $BASE_PATH/log.txt
make BASE_PATH=$BASE_PATH update_paint_go_classification | tee -a $BASE_PATH/log.txt
AFFECTED_TABLES="go_classification go_classification_relationship fullgo_version"
make BASE_PATH=$BASE_PATH update_paint_go_annotation | tee -a $BASE_PATH/log.txt
AFFECTED_TABLES="$AFFECTED_TABLES go_annotation"
make BASE_PATH=$BASE_PATH update_paint_go_evidence | tee -a $BASE_PATH/log.txt  # 17min
AFFECTED_TABLES="$AFFECTED_TABLES go_evidence"
make BASE_PATH=$BASE_PATH update_paint_go_annot_qualifier | tee -a $BASE_PATH/log.txt
AFFECTED_TABLES="$AFFECTED_TABLES go_annotation_qualifier go_evidence_qualifier"
make BASE_PATH=$BASE_PATH switch_evidence_to_pmid | tee -a $BASE_PATH/log.txt
make BASE_PATH=$BASE_PATH delete_incorrect_go_annot_qualifiers | tee -a $BASE_PATH/log.txt
make BASE_PATH=$BASE_PATH update_paint_paint_annotation | tee -a $BASE_PATH/log.txt
AFFECTED_TABLES="$AFFECTED_TABLES paint_annotation"
make BASE_PATH=$BASE_PATH update_paint_paint_evidence | tee -a $BASE_PATH/log.txt  # 19min
AFFECTED_TABLES="$AFFECTED_TABLES paint_evidence"
make BASE_PATH=$BASE_PATH update_paint_paint_annot_qualifier | tee -a $BASE_PATH/log.txt
AFFECTED_TABLES="$AFFECTED_TABLES paint_annotation_qualifier"
make BASE_PATH=$BASE_PATH update_comments_status | tee -a $BASE_PATH/log.txt
AFFECTED_TABLES="$AFFECTED_TABLES comments curation_status"
make BASE_PATH=$BASE_PATH obsolete_redundant_ibds | tee -a $BASE_PATH/log.txt  # 14min
make BASE_PATH=$BASE_PATH setup_preupdate_data | tee -a $BASE_PATH/log.txt
make BASE_PATH=$BASE_PATH gen_iba_gaf_yamls | tee -a $BASE_PATH/log.txt
make BASE_PATH=$BASE_PATH switch_paint_table_names | tee -a $BASE_PATH/log.txt
make BASE_PATH=$BASE_PATH regenerate_go_aggregate_view | tee -a $BASE_PATH/log.txt
make BASE_PATH=$BASE_PATH regenerate_paint_aggregate_view | tee -a $BASE_PATH/log.txt

echo $AFFECTED_TABLES
ELAPSED_TIME=$(($SECONDS - $START_TIME))
echo "Pipeline finished in $ELAPSED_TIME sec"

### Rerun workflow
# ./scripts/run_paint_pipeline.sh
# When undoing changes is desired:
# ./scripts/util/reset_paint_table.sh {AFFECTED_TABLES}
# Then on DB server (/pgres_data/data/paint_refresh/ as user postgres):
# ./restore_paint_table.sh {AFFECTED_TABLES}