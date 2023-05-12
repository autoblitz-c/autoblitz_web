import gspread
from google.oauth2 import service_account
from dotenv import load_dotenv
import os
import pandas as pd
from gspread_dataframe import set_with_dataframe
import time
from datetime import datetime, timedelta
from threading import Lock

load_dotenv() #TODO: changes this
# create a lock for synchronizing access to the Google Sheet
lock = Lock()
credentials_dict = {
    'type': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_TYPE'),
    'project_id': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_PROJECT_ID'),
    'private_key_id': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_PRIVATE_KEY_ID'),
    'private_key': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_PRIVATE_KEY').replace('\\n', '\n'),
    'client_email': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_CLIENT_EMAIL'),
    'client_id': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_CLIENT_ID'),
    'auth_uri': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_AUTH_URI'),
    'token_uri': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_TOKEN_URI'),
    'auth_provider_x509_cert_url': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_AUTH_PROVIDER_X509_CERT_URL'),
    'client_x509_cert_url': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_CLIENT_X509_CERT_URL'),
}
SCOPES = ['https://www.googleapis.com/auth/drive',
          'https://www.googleapis.com/auth/drive.file',
          'https://www.googleapis.com/auth/spreadsheets']

credentials = service_account.Credentials.from_service_account_info(
    credentials_dict,
    scopes=SCOPES)
client = gspread.authorize(credentials)


def add_data(filename: str, sheet_no: int, json_data):
    lock.acquire()
    json_data = [json_data]
    while True:
        try:
            if sheet_no == 1:
                sheet = client.open(filename).worksheet('Sheet1')
                rows = sheet.get_all_values()
                if len(rows) > 1:
                    old_df = pd.DataFrame(rows[1:], columns=rows[0])
                    # convert the list of dictionaries to a pandas DataFrame
                    df = pd.DataFrame(json_data)
                    new_df = pd.concat([old_df, df], axis=0)
                    set_with_dataframe(sheet, new_df)
                else:
                    df = pd.DataFrame(json_data)
                    set_with_dataframe(sheet, df)

            elif sheet_no == 2:
                sheet2 = client.open(filename).worksheet('Sheet2')
                rows2 = sheet2.get_all_values()
                if len(rows2) > 1:
                    old_df = pd.DataFrame(rows2[1:], columns=rows2[0])
                    # convert the list of dictionaries to a pandas DataFrame
                    df = pd.DataFrame(json_data)
                    new_df = pd.concat([old_df, df], axis=0)
                    set_with_dataframe(sheet2, new_df)
                else:
                    df = pd.DataFrame(json_data)
                    set_with_dataframe(sheet2, df)

            break
        except:
            time.sleep(40)
            continue
    lock.release()
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
    lock.acquire()
    if sheet_no == 1:
        print("going")
        sheet = client.open(filename).worksheet('Sheet1')
        data = sheet.get_all_values()
        headers = data.pop(0)
        df = pd.DataFrame(data, columns=headers)
        # Define the column names and values to match
        match_column_name = match_col  # Replace with the name of your column to match
        match_value = match_value  # Replace with the value to match
        filtered_df = df[df[match_column_name] == match_value]
        filtered_dic = filtered_df.to_dict(orient='records')
        if len(filtered_dic) != 0:
            lock.release()
            return filtered_dic[0]
        else:
            lock.release()
            return 0

    elif sheet_no == 2:
        print("going")
        sheet2 = client.open(filename).worksheet('Sheet2')
        data = sheet2.get_all_values()
        headers = data.pop(0)
        df = pd.DataFrame(data, columns=headers)
        # Define the column names and values to match
        match_column_name = match_col  # Replace with the name of your column to match
        match_value = match_value  # Replace with the value to match
        filtered_df = df[df[match_column_name] == match_value]
        filtered_dic = filtered_df.to_dict(orient='records')
        if len(filtered_dic) != 0:
            lock.release()
            return filtered_dic[0]
        else:
            lock.release()
            return 0



"""data = open("static/booking/autoblitz97453.json")
book = json.load(data)
print(book['name'])
add_data("Customer_data", book)"""


#response = {"orderNo": "12345", "date": "2023-05-12", "time": "12.20", "mail": "tau@gmail.com", "payment_type": "cash", "amount": "2500",
            #"refund_amount": "1500", "reason": "hi"}
#add_data("Customer_data", 2, response)
#print(query_data("Customer_data",'orderNo', '1234', 2))
