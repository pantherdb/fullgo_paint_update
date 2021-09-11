import argparse
import json
import os
from urllib.parse import urlparse, urljoin

parser = argparse.ArgumentParser()
parser.add_argument('-r', '--release_date_json')
parser.add_argument('-d', '--downloaded_file_list')

go_release_base_url = "http://release.geneontology.org/"

if __name__ == "__main__":
    args = parser.parse_args()

    with open(args.release_date_json) as df:
        date_j = json.load(df)
        release_date = date_j['date']

    source_files = []
    with open(args.downloaded_file_list) as fl:
        for l in fl.readlines():
            # if l.endswith(".gaf.gz"):
            source_files.append(l.rstrip())

    print("GO release date:", release_date)
    for sf in source_files:
        dated_release_base_url = urljoin(go_release_base_url, release_date)
        relative_path = urlparse(sf).path  # Ex: /products/annotations/paint_other.gaf.gz
        full_release_url = dated_release_base_url + relative_path
        print(full_release_url)

    print()  # Newline separator
    print("This data can be retrieved at any time from", dated_release_base_url)
    print()
    print("Notes")
    print("-----")