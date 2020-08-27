import csv
import os
import argparse
import datetime
from collections import Counter
from util.publish_google_sheet import SheetPublishHandler, Sheet

parser = argparse.ArgumentParser()
parser.add_argument('-b', '--before_release_folder_root')
parser.add_argument('-a', '--after_release_folder_root')
parser.add_argument('-s', '--startdate', help="Formatted like '20200201'")
parser.add_argument('-p', '--publish_report', action='store_const', const=True)
parser.add_argument('-o', '--skip_other', action='store_const', const=True)
parser.add_argument('-u', '--panther_blacklist', help='panther_blacklist.txt built from UniProt GPI')

args = parser.parse_args()

### Get current release (the "before" if comparing before pushing a new IBA release)
# Specify local path or URL to wget
# args.before_release_folder_root = "current"
# $ wget -r ftp://ftp.pantherdb.org/downloads/paint/{before_release_folder_root}/
# $ gunzip {base_folder}/presubmission/*

# Specify local path or URL to wget
# args.after_release_folder_root = "14.1/2020-03-26"
# base_folder = os.path.split(args.after_release_folder_root)[-1]
# $ wget -r -nH --no-parent --cut-dirs=4 ftp://ftp.pantherdb.org/downloads/paint/{after_release_folder_root}/ -P {base_folder}
# $ gunzip {base_folder}/presubmission/*
# $ python3 scripts/compare_paint_releases.py -b 2020-01-31 -a 2020-03-26 -s 20200131


def parse_ptn_terms_from_ibd(filepath, startdate=None):
    new_annotations = set()
    with open(filepath) as ibd_f:
        reader = csv.reader(ibd_f, delimiter="\t")
        for r in reader:
            if r[0].startswith("!"):
                continue
            # Check date is after startdate
            date = r[13]
            if startdate is None or date > startdate:
                ptn = r[1]
                term = r[4]
                qual = r[3]
                if "NOT" in qual:
                    continue
                new_annotations.add((ptn, term))
    return new_annotations

def parse_ptn_terms_from_ibd_before_startdate_intersect(filepath, startdate, annot_tuples):
    new_annotations = set()
    with open(filepath) as ibd_f:
        reader = csv.reader(ibd_f, delimiter="\t")
        for r in reader:
            if r[0].startswith("!"):
                continue
            # Check date is before startdate
            date = r[13]
            if date < startdate:
                ptn = r[1]
                term = r[4]
                qual = r[3]
                ibd_tuple = (ptn, term)
                if "NOT" in qual:
                    continue
                # The 'intersect' part of the function
                if ibd_tuple not in annot_tuples:
                    continue
                new_annotations.add(ibd_tuple)
    return new_annotations


def parse_panther_blacklist(panther_blacklist):
    uniprot_ids = []
    with open(panther_blacklist) as bf:
        for l in bf.readlines():
            uniprot_ids.append(f"UniProtKB:{l.rstrip()}")
    return uniprot_ids


panther_blacklist = None
if args.panther_blacklist:
    panther_blacklist = parse_panther_blacklist(args.panther_blacklist)

handler = SheetPublishHandler()
date_str = datetime.date.today().isoformat()
sheet_title = "{}-update_stats".format(date_str)
sheet = Sheet(title=sheet_title)

# Set of PTN-to-term tuples
# E.g. {(PTN000003938, GO:0006355), (PTN000007715, GO:0000122)}
after_ibd_file = os.path.join(args.after_release_folder_root, "IBD.gaf")
# print("Parsing out new IBDs created after", args.startdate)
# new_annotations = parse_ptn_terms_from_ibd(after_ibd_file, args.startdate)
# print(len(new_annotations), "distinct new IBDs since", args.startdate)
after_annotations = parse_ptn_terms_from_ibd(after_ibd_file)
print(len(after_annotations), "total distinct IBDs in 'after' IBD file")
before_ibd_file = os.path.join(args.before_release_folder_root, "IBD.gaf")
before_annotations = parse_ptn_terms_from_ibd(before_ibd_file)
print(len(before_annotations), "total distinct IBDs in 'before' IBD file")

# Compare two sets of IBDs, before and after. Get differences:
# (after) - (before) = new IBDs
new_ibds = after_annotations - before_annotations
if args.startdate:
    # Find restored IBDs - defined as: IBD in new IBD.gaf w/ date < previous release BUT this IBD not in previous IBD.gaf
    new_ibds_created_before_startdate = parse_ptn_terms_from_ibd_before_startdate_intersect(after_ibd_file, args.startdate, new_ibds)
    print(len(new_ibds_created_before_startdate), "restored IBDs")
    new_ibds = parse_ptn_terms_from_ibd(after_ibd_file, args.startdate)
    print(len(new_ibds), "new IBDs since", args.startdate)
else:
    print(len(new_ibds), "new IBDs via set comparison")
sheet.append_row(["Added IBDs", len(new_ibds)])

# (before) - (after) = obsoleted IBDs
obsoleted_ibds = before_annotations - after_annotations
print(len(obsoleted_ibds), "obsoleted IBDs via set comparison")
sheet.append_row(["Obsoleted IBDs", len(obsoleted_ibds)])

def parse_ptn_from_with_from(with_from):
    curies = with_from.split("|")
    curie_map = {}  # Will overwrite reoccuring namespaces
    for c in curies:
        curie_bits = c.split(":")
        if len(curie_bits) == 2:
            ns, val = curie_bits
            curie_map[ns] = val
    return curie_map.get("PANTHER", "")


# Count how many IBAs in new release match new_ibds
def get_ibd_to_iba_counts(iba_folder, ibd_tuples):
    iba_count_by_file = {}
    all_iba_count_by_file = {}
    taxons = {}
    for iba_filename in os.listdir(iba_folder):
        if args.skip_other and "paint_other" in iba_filename:  # Only here to increase testing speed
            continue
        iba_file = os.path.join(iba_folder, iba_filename)
        print("Parsing", iba_file)
        with open(iba_file) as iba_f:
            iba_file_base = os.path.basename(iba_file)
            iba_count_by_file[iba_file] = 0
            all_iba_count_by_file[iba_file_base] = 0
            reader = csv.reader(iba_f, delimiter="\t")
            for r in reader:
                if r[0].startswith("!"):
                    continue
                ptn = parse_ptn_from_with_from(r[7])
                term = r[4]
                iba_tuple = (ptn, term)
                if iba_tuple in ibd_tuples:
                    iba_count_by_file[iba_file] += 1
                all_iba_count_by_file[iba_file_base] += 1

                # Grab UniProt and taxon data
                uniprot = r[10].split("|", maxsplit=1)[0]
                taxon = r[12]
                if taxon not in taxons:
                    taxons[taxon] = []
                taxons[taxon].append(uniprot)
    return iba_count_by_file, all_iba_count_by_file, taxons


after_iba_folder = os.path.join(args.after_release_folder_root, "presubmission")
added_iba_count_by_file, all_iba_counts_after, taxons_after = get_ibd_to_iba_counts(after_iba_folder, new_ibds)
added_iba_count = sum([count for iba_file, count in added_iba_count_by_file.items()])

# Count how many IBAs in before release match obsoleted_ibds
before_iba_folder = os.path.join(args.before_release_folder_root, "presubmission")
dropped_iba_count_by_file, all_iba_counts_before, taxons_before = get_ibd_to_iba_counts(before_iba_folder, obsoleted_ibds)
dropped_iba_count = sum([count for iba_file, count in dropped_iba_count_by_file.items()])

for f, count in added_iba_count_by_file.items():
    print(count, "IBAs added in", f)
print(added_iba_count, "added IBAs")
sheet.append_row(["Added IBAs", added_iba_count])
print(dropped_iba_count, "dropped IBAs")
sheet.append_row(["Obsoleted IBAs", dropped_iba_count])
print("Net increase:", added_iba_count - dropped_iba_count)
sheet.append_row(["Net IBA change", added_iba_count - dropped_iba_count])

all_iba_files = set(list(all_iba_counts_before.keys()) + list(all_iba_counts_after.keys()))
headers = [
    "Filename",
    f"IBA count {args.before_release_folder_root}",
    f"IBA count {args.after_release_folder_root}",
    "Percent change"
]
print("\t".join(headers))
sheet.append_row([])
sheet.append_row(headers)
for iba_filename in sorted(all_iba_files):
    before_count = all_iba_counts_before.get(iba_filename, 0)
    after_count = all_iba_counts_after.get(iba_filename, 0)
    percent_change = "%.2f" % (((after_count - before_count) / before_count) * 100)
    print_row = [iba_filename, before_count, after_count, percent_change]
    print("\t".join([str(i) for i in print_row]))
    sheet.append_row(print_row)
before_total_count = sum([count for iba_file, count in all_iba_counts_before.items()])
after_total_count = sum([count for iba_file, count in all_iba_counts_after.items()])
total_percent_change = "%.2f" % (((after_total_count - before_total_count) / before_total_count) * 100)
total_row = ["Total", before_total_count, after_total_count, total_percent_change]
print("\t".join([str(i) for i in total_row]))
sheet.append_row(total_row)

uniprot_blacklisted_ids = ["P12345", "P12346", "P12347", "P12348"]
all_taxons = set(list(taxons_before.keys()) + list(taxons_after.keys()))
taxon_headers = [
    "Taxon",
    f"Annot count {args.before_release_folder_root}",
    f"Annot count {args.after_release_folder_root}",
    "Percent change",
    "% dropped by UniProt GPI check"
]
print("\t".join(taxon_headers))
sheet.append_row([])
sheet.append_row(taxon_headers)
for taxon in sorted(all_taxons):
    before_ids = taxons_before.get(taxon, [])
    before_count = len(before_ids)
    after_ids = taxons_after.get(taxon, [])
    after_count = len(after_ids)
    blacklisted_count = 0
    if panther_blacklist:
        before_counts_by_id = Counter(before_ids)
        after_counts_by_id = Counter(after_ids)
        for uniprot_id in panther_blacklist:
            if uniprot_id in before_counts_by_id:
                blacklisted_count += before_counts_by_id[uniprot_id]
        bl_percent_change = "%.2f" % ((blacklisted_count / before_count) * 100)
    percent_change = "%.2f" % (((after_count - before_count) / before_count) * 100)
    print_row = [taxon, before_count, after_count, percent_change]
    if panther_blacklist:
        print_row = print_row + [bl_percent_change]
    print("\t".join([str(i) for i in print_row]))
    sheet.append_row(print_row)

if args.publish_report:
    handler.publish_sheet(sheet)
    print(f"Published {sheet.title}")