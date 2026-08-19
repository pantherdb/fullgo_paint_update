#!/bin/bash
set -euo pipefail

# Extract experimental PAINT annotations (gene product, GO term, reference, evidence, with-from)
# from the previous GO release's GAF and left-join against the new release's obsolete_go_terms.txt
# (obsolete_term -> replacement_term). Where a replacement exists, swap it into the GO term column
# and drop the replacement column, producing a 5-column TSV of refreshed experimental annotations.
join -t "	" -a 1 -1 2 -o 1.1,1.2,2.2,1.3,1.4,1.5 \
    <(grep -v -e "^\!" $PREV_PAINT_EXP_GAF | cut -f2,5,6,7,15 | sort -k2) \
    <(sort $BASE_PATH/obsolete_go_terms.txt) \
    | awk -F'\t' 'BEGIN{OFS="\t"} {if ($3 != "") $2 = $3; print $1, $2, $4, $5, $6}' \
    | sort \
    > $BASE_PATH/Pthr_GO_prev_exp_query.tsv

# Match the refreshed query rows against the new release's full Pthr_GO TSV: for each line in
# $FULL_GO_TSV, emit it if some query row's 5 fields all appear as substrings of the line.
awk -F'\t' 'NR==FNR {queries[$1"\t"$2"\t"$3"\t"$4"\t"$5]; next}
{
  for (query in queries) {
    split(query, parts, "\t")
    if (index($0, parts[1]) && index($0, parts[2]) &&
        index($0, parts[3]) && index($0, parts[4]) &&
        index($0, parts[5])) {
      print
      break
    }
  }
}' $BASE_PATH/Pthr_GO_prev_exp_query.tsv $FULL_GO_TSV \
    > $MATCH_OUT

# Everything that did NOT match: the annotations PAINT should load. $FILTERED_OUT carries the
# PANTHER version from the Makefile - it used to be hardcoded to 19.0.
cat $MATCH_OUT | grep -v -f /dev/stdin $FULL_GO_TSV > $FILTERED_OUT
