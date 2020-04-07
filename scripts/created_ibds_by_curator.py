from pthr_db_caller.db_caller import DBCaller
from util.publish_google_sheet import SheetPublishHandler, Sheet
import argparse
import json
import datetime

parser = argparse.ArgumentParser()
parser.add_argument('-b', '--before_date')
parser.add_argument('-a', '--after_date')
parser.add_argument('-p', '--publish_report', action='store_const', const=True)

args = parser.parse_args()

query_file = "scripts/sql/reports/created_ibds_by_curator.sql"

caller = DBCaller()
q_vars = {"before_date": args.before_date, "after_date": args.after_date}
results = caller.run_cmd_line_args(query_file, query_variables=json.dumps(q_vars), no_header_footer=True)

handler = SheetPublishHandler()
date_str = datetime.date.today().isoformat()
sheet_title = "{}-ibd_count_by_curator".format(date_str)
sheet = Sheet(title=sheet_title)

headers = ["Name", f"IBDs created between {args.before_date} and {args.after_date}"]
sheet.append_row(headers)
total_count = 0
for r in results[1:]:
    curator_name = r[0]
    count = r[1]
    total_count += count
    sheet.append_row([curator_name, count])
sheet.append_row(["Total", total_count])

if args.publish_report:
    handler.publish_sheet(sheet)
    print(f"Published {sheet.title}")