import argparse
import json
import os
from urllib.parse import urlparse, urljoin

parser = argparse.ArgumentParser()
parser.add_argument('-r', '--release_date_json')
parser.add_argument('-d', '--downloaded_file_list')

# go_release_base_url = "http://release.geneontology.org/"
# go_current_base_url = "http://current.geneontology.org/"
go_release_base_url = "https://ftp.ebi.ac.uk/pub/contrib/goa/goex/releases/"
go_current_base_url = "https://ftp.ebi.ac.uk/pub/contrib/goa/goex/current/"

if __name__ == "__main__":
    args = parser.parse_args()

    with open(args.release_date_json) as df:
        if args.release_date_json.endswith(".txt"):
            release_date = df.readline().rstrip()
        else:
            date_j = json.load(df)
            release_date = date_j['date']

    source_files = []
    with open(args.downloaded_file_list) as fl:
        for l in fl.readlines():
            # if l.endswith(".gaf.gz"):
            source_files.append(l.rstrip())

    print("GO release date:", release_date)
    for sf in source_files:
        dated_release_base_url = os.path.join(go_release_base_url, release_date)
        # relative_path = urlparse(sf).path  # Ex: /products/annotations/paint_other.gaf.gz
        relative_path = sf.replace(go_current_base_url, "")  # Ex: uniprot-centric/gaf/CHICK_9031_UP000000539.gaf.gz
        full_release_url = os.path.join(dated_release_base_url, relative_path)
        print(full_release_url)

    print()  # Newline separator
    print("This data can be retrieved at any time from", dated_release_base_url)
    print()
    print("Notes")
    print("-----")