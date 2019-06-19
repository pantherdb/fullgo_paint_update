import argparse

# from db_caller_old import DBCaller
from pthr_db_caller.db_caller import DBCaller
# import pthr_db_caller

parser = argparse.ArgumentParser()
parser.add_argument("query_filename")
# Only use query variables for single query SQL files, otherwise managing these gets tricky due to the per-statement cleaning step.
parser.add_argument("-v", "--query_variables", type=str, required=False, help="comma-delimited, ordered list of values to replace variables in SQL script.\
                                                Only use query variables for single query SQL files, otherwise managing these gets tricky due to the per-statement cleaning step.")
parser.add_argument("-o", "--rows_outfile", help="Write result rows to specified filename.")
parser.add_argument("-d", "--delimiter", help="column delimiter to display in query output.")
parser.add_argument("-n", "--no_header_footer", action='store_const', const=True, help="No header or footer will be included in query result output")

args = parser.parse_args()

caller = DBCaller()
caller.run_cmd_line_args(args.query_filename, query_variables=args.query_variables, rows_outfile=args.rows_outfile, delimiter=args.delimiter, no_header_footer=args.no_header_footer)