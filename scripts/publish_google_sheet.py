# from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
# SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
#     'https://www.googleapis.com/auth/spreadsheets.readonly']
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE = None

class SheetRow:
    def __init__(self, values=None):
        self.values = []
        if values:
            self.values = values

    def to_dict(self):
        rows_dict = {"values": []}
        for v in self.values:
            rows_dict["values"].append({
                        "userEnteredValue": {
                            "stringValue": v
                            }
                        })
        return rows_dict

class Sheet:
    def __init__(self, title):
        self.title = title
        self.spreadsheet_id = None
        self.rows = []  # [SheetRow]

    def append_row(self, row_values):
        self.rows.append(SheetRow(values=row_values))

    def get_data(self):
        data = [
            {
                "data": [
                    {
                        "rowData": [r.to_dict() for r in self.rows]
                    }
                ]
            }
        ]
        return data


class SheetPublishHandler:
    def __init__(self):
        self.service = None
        self.setup()

    def setup(self):
        """Shows basic usage of the Drive v3 API.
        Prints the names and ids of the first 10 files the user has access to.
        """
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'resources/sheets_credentials.json', SCOPES)
                creds = flow.run_local_server()
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('sheets', 'v4', credentials=creds)

    def create_sheet(self, title, values):
        spreadsheet = {'properties': {'title': title},
            'sheets': values}
        sheet_meta = self.service.spreadsheets().create(body=spreadsheet,fields='spreadsheetId').execute()
        return sheet_meta

    def publish_sheet(self, sheet):
        meta = self.create_sheet(sheet.title, values=sheet.get_data())
        sheet.spreadsheet_id = meta['spreadsheetId']


def main():
    handler = SheetPublishHandler()

    sheet = Sheet(title='test sheet')
    sheet.append_row(["whatup"])
    sheet.append_row(["sup", "yee", "yo"])

    handler.publish_sheet(sheet)


if __name__ == '__main__':
    main()