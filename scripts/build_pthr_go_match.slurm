#!/bin/bash
#SBATCH --time=2:00:00
#SBATCH --ntasks=1
#SBATCH --mem=16gb
#SBATCH --account=$HPC_ACCOUNT
#SBATCH --partition=thomas
#SBATCH --mail-type=END,FAIL

BASE_PATH=$BASE_PATH \
    PREV_PAINT_EXP_GAF=$PREV_PAINT_EXP_GAF \
    FULL_GO_TSV=$FULL_GO_TSV \
    MATCH_OUT=$MATCH_OUT \
    FILTERED_OUT=$FILTERED_OUT \
    bash scripts/build_pthr_go_match.sh
