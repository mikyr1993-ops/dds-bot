import os
import json
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
SHEET_NAME = os.environ.get("SHEET_NAME", "Расходы")

HEADERS = ["Дата", "Сумма", "Категория", "Тип оплаты", "Кто записал"]


def get_sheet():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")

    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)

    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    try:
        sheet = spreadsheet.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=10)

    # Заголовки если лист пустой
    existing = sheet.row_values(1)
    if not existing:
        sheet.append_row(HEADERS, value_input_option="USER_ENTERED")

    return sheet


def append_row(row: list):
    sheet = get_sheet()
    sheet.append_row(row, value_input_option="USER_ENTERED")
