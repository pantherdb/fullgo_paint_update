import argparse
import os
from urllib.parse import urlparse
from util.release_date import read_release_date


def relative_to_base(url, base_url):
    """Path of url relative to base_url, comparing paths only.

    The GO directory listing returns absolute http:// hrefs even when downloads run
    over https://, so a plain string strip of base_url leaves the whole URL behind.
    """
    base_path = urlparse(base_url).path
    path = urlparse(url).path
    if path.startswith(base_path):
        path = path[len(base_path):]
    return path.lstrip("/")


parser = argparse.ArgumentParser()
parser.add_argument('-r', '--release_date_json')
parser.add_argument('-d', '--downloaded_file_list')
parser.add_argument('-c', '--current_base_url', default="https://current.geneontology.org/",
                    help="Base URL the files were downloaded from, stripped to get each relative path. "
                         "GOEx: https://ftp.ebi.ac.uk/pub/contrib/goa/goex/current/")
parser.add_argument('-b', '--release_base_url', default="https://release.geneontology.org/",
                    help="Base URL of the dated release archive the files can be retrieved from later. "
                         "GOEx: https://ftp.ebi.ac.uk/pub/contrib/goa/goex/releases/")

if __name__ == "__main__":
    args = parser.parse_args()

    release_date = read_release_date(args.release_date_json)

    source_files = []
    with open(args.downloaded_file_list) as fl:
        for l in fl.readlines():
            # if l.endswith(".gaf.gz"):
            source_files.append(l.rstrip())

    dated_release_base_url = os.path.join(args.release_base_url, release_date)

    print("GO release date:", release_date)
    for sf in source_files:
        relative_path = relative_to_base(sf, args.current_base_url)  # Ex: annotations/gaf/CHICK-uniprot.gaf.gz
        full_release_url = os.path.join(dated_release_base_url, relative_path)
        print(full_release_url)

    print()  # Newline separator
    print("This data can be retrieved at any time from", dated_release_base_url)
    print()
    print("Notes")
    print("-----")
