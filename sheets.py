import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

MONTH_NAMES = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
}

def get_sheet():
    creds_json = os.environ["GOOGLE_CREDENTIALS_JSON"]
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(os.environ["SPREADSHEET_ID"])
    now = datetime.now()
    sheet_name = f"{MONTH_NAMES[now.month]} {now.year}"
    return spreadsheet.worksheet(sheet_name)

def append_row(row):
    sheet = get_sheet()
    col_a = sheet.col_values(1)
    next_row = len(col_a) + 1
    # Пишем A-D и F, пропускаем E (назначение — ручное)
    sheet.update(f"A{next_row}:D{next_row}", [row[:4]])
    sheet.update(f"F{next_row}", [[row[5]]])
