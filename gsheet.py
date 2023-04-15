import gspread
from google.oauth2 import service_account
from dotenv import load_dotenv
import os
import json
import time
from datetime import datetime, timedelta

load_dotenv()

credentials_dict = {
    'type': os.getenv('GOOGLE_APPLICATION_CREDENTIALS_TYPE'),
    'project_id': os.getenv('GOOGLE_APPLICATION_CREDENTIALS_PROJECT_ID'),
    'private_key_id': os.getenv('GOOGLE_APPLICATION_CREDENTIALS_PRIVATE_KEY_ID'),
    'private_key': os.getenv('GOOGLE_APPLICATION_CREDENTIALS_PRIVATE_KEY').replace('\\n', '\n'),
    'client_email': os.getenv('GOOGLE_APPLICATION_CREDENTIALS_CLIENT_EMAIL'),
    'client_id': os.getenv('GOOGLE_APPLICATION_CREDENTIALS_CLIENT_ID'),
    'auth_uri': os.getenv('GOOGLE_APPLICATION_CREDENTIALS_AUTH_URI'),
    'token_uri': os.getenv('GOOGLE_APPLICATION_CREDENTIALS_TOKEN_URI'),
    'auth_provider_x509_cert_url': os.getenv('GOOGLE_APPLICATION_CREDENTIALS_AUTH_PROVIDER_X509_CERT_URL'),
    'client_x509_cert_url': os.getenv('GOOGLE_APPLICATION_CREDENTIALS_CLIENT_X509_CERT_URL'),
}
SCOPES = ['https://www.googleapis.com/auth/drive',
          'https://www.googleapis.com/auth/drive.file',
          'https://www.googleapis.com/auth/spreadsheets']

credentials = service_account.Credentials.from_service_account_info(
    credentials_dict,
    scopes=SCOPES)
client = gspread.authorize(credentials)


def add_data(filename: str, sheet_no: int, json_data):
    while True:
        try:
            if sheet_no == 1:
                sheet = client.open(filename).worksheet('Sheet1')
                if len(sheet.row_values(1)) == 0:
                    data = list(str(i) for i in json_data.keys())
                    # Get the existing row data
                    sheet.insert_row(data, 1)
                    values = list(json_data.values())
                    sheet.append_row(values)
                else:
                    header = sheet.row_values(1)
                    values = []
                    for col in header:
                        if col in json_data.keys():
                            values.append(json_data[col])
                        else:
                            values.append("NA")
                    sheet.append_row(values)
            elif sheet_no == 2:
                sheet2 = client.open(filename).worksheet('Sheet2')
                if len(sheet2.row_values(1)) == 0:
                    data = list(str(i) for i in json_data.keys())
                    # Get the existing row data
                    sheet2.insert_row(data, 1)
                    values = list(json_data.values())
                    sheet2.append_row(values)
                    print("data added")
                else:
                    header = sheet2.row_values(1)
                    values = []
                    for col in header:
                        if col in json_data.keys():
                            values.append(json_data[col])
                        else:
                            values.append("NA")
                    sheet2.append_row(values)
                    print("data added")

            break
        except:
            time.sleep(40)
            continue
    return "done"


def delete_data(filename: str, days: int, sheet_no: int):
    if sheet_no == 1:
        sheet = client.open(filename).worksheet('Sheet1')
        # Get the data from the sheet
        data = sheet.get_all_records()

        # Delete rows where the date column value is greater than 360 days
        for row in data:
            date_str = row['date']  # Replace 'Date' with the name of your date column
            date = datetime.strptime(date_str, '%Y/%m/%d')  # Parse the date string into a datetime object
            if datetime.today() - date >= timedelta(days=days):
                sheet.delete_row(sheet.find(date_str).row)
    elif sheet_no == 2:
        sheet2 = client.open(filename).worksheet('Sheet2')
        # Get the data from the sheet
        data = sheet2.get_all_records()

        # Delete rows where the date column value is greater than 360 days
        for row in data:
            date_str = row['date']  # Replace 'Date' with the name of your date column
            date = datetime.strptime(date_str, '%Y/%m/%d')  # Parse the date string into a datetime object
            if datetime.today() - date >= timedelta(days=days):
                sheet2.delete_row(sheet2.find(date_str).row)


def query_data(filename: str, match_col: str, match_value: str, sheet_no: int):
    if sheet_no == 1:
        print("going")
        sheet = client.open(filename).worksheet('Sheet1')
        # Define the column names and values to match
        match_column_name = match_col  # Replace with the name of your column to match
        match_value = match_value  # Replace with the value to match

        # Find the rows that match the column value
        cell_list = sheet.findall(match_value, in_column=sheet.find(match_column_name).col)

        for cell in cell_list:
            row_values = sheet.row_values(cell.row)
            row_dict = {sheet.cell(1, col).value: row_values[col - 1] for col in range(1, len(row_values) + 1)}
            return row_dict






    elif sheet_no == 2:
        sheet2 = client.open(filename).worksheet('Sheet2')
        # Define the column names and values to match
        match_column_name = match_col  # Replace with the name of your column to match
        match_value = match_value  # Replace with the value to match

        # Find the rows that match the column value
        cell_list = sheet2.findall(match_value, in_column=sheet2.find(match_column_name).col)

        # Get the values for all columns in the matching rows
        return_values = []
        for cell in cell_list:
            row_values = sheet2.row_values(cell.row)
            row_dict = {sheet2.cell(1, col).value: row_values[col - 1] for col in range(1, len(row_values) + 1)}
            return row_dict


"""data = open("static/booking/autoblitz97453.json")
book = json.load(data)
print(book['name'])
add_data("Customer_data", book)"""
response = {"orderNo": "1234", "mail": "tau@gmail.com", "amount": "2500",
            "refund_amount": "1500", "reason": "hi"}
# print(add_data("Customer_data", 2, response))
# print(query_data("Customer_data",'orderNo', 'ct8-6z0')['orderGUID'])
