import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument('-j', '--date_json')
parser.add_argument('-d', '--doi_json')
parser.add_argument('-p', '--panther_version')


if __name__ == "__main__":
    args = parser.parse_args()

    with open(args.date_json) as df:
        if args.date_json.endswith(".txt"):
            release_date = df.readline().rstrip()
        else:
            date_j = json.load(df)
            release_date = date_j['date']
    print("\t".join(["GO", release_date]))

    if args.doi_json:
        with open(args.doi_json) as df:
            doi_j = json.load(df)
            doi = doi_j['doi']
        print("\t".join(["DOI GO", doi]))

    print("\t".join(["PANTHER", f"v.{args.panther_version}"]))
