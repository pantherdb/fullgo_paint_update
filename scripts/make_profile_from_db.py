import argparse
from pthr_db_caller.db_caller import DBCaller

parser = argparse.ArgumentParser()
parser.add_argument('outfile')

args = parser.parse_args()

caller = DBCaller()

query = "select go_annotation_release_date, panther_version from panther_upl.fullgo_version;"

results = caller.run_cmd_line_args(query.rstrip(), no_header_footer=True)

version_date = results[1][0]
panther_version = results[1][1]

with open(args.outfile, "w+") as out_f:
    out_f.write("GO\t{}\n".format(version_date))
    out_f.write("PANTHER\tv.{}".format(panther_version))