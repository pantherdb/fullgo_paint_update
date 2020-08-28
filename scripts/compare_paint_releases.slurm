#!/bin/bash
#SBATCH --time=3:00:00
#SBATCH --ntasks=1
#SBATCH --mem=96gb
#SBATCH --account=lc_pdt
#SBATCH --partition=thomas
#SBATCH --mail-type=END,FAIL

. env/bin/activate

python3 scripts/compare_paint_releases.py -b $BEFORE_DATE -a $AFTER_DATE -u $BASE_PATH/resources/panther_blacklist.txt -j $BASE_PATH/update_stats.json