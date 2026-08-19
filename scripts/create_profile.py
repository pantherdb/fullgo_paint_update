import argparse
import json
from util.release_date import read_release_date

parser = argparse.ArgumentParser()
parser.add_argument('-j', '--date_json')
parser.add_argument('-d', '--doi_json')
parser.add_argument('-p', '--panther_version')


if __name__ == "__main__":
    args = parser.parse_args()

    release_date = read_release_date(args.date_json)
    print("\t".join(["GO", release_date]))

    if args.doi_json:
        with open(args.doi_json) as df:
            doi_j = json.load(df)
            doi = doi_j['doi']
        print("\t".join(["DOI GO", doi]))

    print("\t".join(["PANTHER", f"v.{args.panther_version}"]))
