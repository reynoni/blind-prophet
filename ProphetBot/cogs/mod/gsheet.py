# This module enables gsheet integrations with python using the googleapi

# Import all the important things
from __future__ import print_function
import pickle, logging
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


class gsheet(object):  # Defining a gsheet, stolen from elsewhere, Nick doesn't understand this.
    def __init__(self):
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        self.creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('./ProphetBot/cogs/mod/credentials.json', SCOPES)
                self.creds = flow.run_local_server()
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)

        self.service = build('sheets', 'v4', credentials=self.creds)

    def get_token_expiry(self):
        print(f'Token expires at {self.creds.expiry}')
        return self.creds.expiry

    def refresh_if_expired(self):
        if not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('./ProphetBot/cogs/mod/credentials.json', SCOPES)
                self.creds = flow.run_local_server()
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)
        
    def add(self,sheetid,sheetrange,ivalue,majorD): #Add rows to a spreadsheet.
        # Call the Sheets API
        sheet = self.service.spreadsheets()
        values = ivalue
        logging.info(f'{values}')
        body = { #configure list for proper insert
            'majorDimension': majorD,
            'values': values
        }
        # The money-maker, the insert.
        self.refresh_if_expired()
        result = sheet.values().append(spreadsheetId=sheetid, range=sheetrange, valueInputOption='USER_ENTERED', body=body).execute() 

    def set(self,sheetid,sheetrange,ivalue,majorD): #Input data into a cell/range, doesn't add rows, overwrites data.
        # Call the Sheets API
        sheet = self.service.spreadsheets()
        value_input_option = 'USER_ENTERED'
        values = ivalue
        # values = []
        # values.append(ivalue)
        body = {
            'majorDimension': majorD,
            'range': sheetrange,
            'values': values
        }
        # The data push.
        self.refresh_if_expired()
        result = sheet.values().update(spreadsheetId=sheetid, range=sheetrange, valueInputOption=value_input_option, body=body).execute()
        
    def clear(self,sheetid,sheetrange):
        sheet = self.service.spreadsheets()
        body = {}
        self.refresh_if_expired()
        resultClear = sheet.values().clear(spreadsheetId=sheetid, range=sheetrange, body=body).execute()

    def get(self,sheetid,sheetrange,render_option): #Pull data from a spreadhseet.
        # Call the Sheets API
        sheet = self.service.spreadsheets()
        date_time_render_option = 'FORMATTED_STRING'

        # The return.
        self.refresh_if_expired()
        result = sheet.values().get(spreadsheetId=sheetid, range=sheetrange, valueRenderOption=render_option, dateTimeRenderOption=date_time_render_option).execute()
        return result   


