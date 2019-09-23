from pthr_db_caller.db_caller import DBCaller
from util.publish_google_sheet import SheetPublishHandler, Sheet
import datetime

CALLER = DBCaller()

query = """
select c.accession, cst.status, u.name, cs.creation_date from panther_upl.curation_status cs
--select count(*) from curation_status cs
join panther_upl.classification c on c.classification_id = cs.classification_id
join panther_upl.users u on u.user_id = cs.user_id
join panther_upl.curation_status_type cst on cst.status_type_sid = cs.status_type_sid
where c.classification_version_sid = 26
--and cs.creation_date > '{}'
order by cs.creation_date desc;
"""

start_date = "2019-06-01"
results = CALLER.run_cmd_line_args(query.format(start_date), no_header_footer=True)

date_str = datetime.date.today().isoformat()
sheet_title = "{}_curation_status".format(date_str)
sheet = Sheet(title=sheet_title)
headers = ["PTHR ID", "status", "name", "creation_date"]
sheet.append_row(headers)

for r in results[1:]:
    family = r[0]
    status = r[1]
    curator = r[2]
    status_creation_date = r[3]
    # print(str(status_creation_date))
    row = [family, status, curator, status_creation_date]
    sheet.append_row(row)

handler = SheetPublishHandler()
handler.publish_sheet(sheet)