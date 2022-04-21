import bisect
import gspread
import json
import os
from time import perf_counter
from ProphetBot.constants import TIERS, SHOP_TIERS


class GsheetsClient(object):
    
    def __init__(self):
        # Initial _auth
        start = perf_counter()
        self._auth = gspread.service_account_from_dict(json.loads(os.environ['GOOGLE_SA_JSON']))
        end = perf_counter()
        print(f'Time to load auth: {end - start}s')

        # Open workbooks
        start = perf_counter()
        self.bpdia_workbook = self._auth.open_by_key(os.environ['SPREADSHEET_ID'])
        self.inv_workbook = self._auth.open_by_key(os.environ['INV_SPREADSHEET_ID'])
        end = perf_counter()
        print(f'Time to load workbooks (2): {end - start}s')

        # Open individual sheets
        start = perf_counter()
        self.char_sheet = self.bpdia_workbook.worksheet('Characters')
        self.log_sheet = self.bpdia_workbook.worksheet('Log')
        self.log_archive = self.bpdia_workbook.worksheet('Archive Log')
        self.arenas_sheet = self.bpdia_workbook.worksheet('Arenas')
        self.adventures_sheet = self.bpdia_workbook.worksheet('Adventures')
        end = perf_counter()
        print(f'Time to load sheets (5): {end - start}s')

    def reload(self):
        self.__init__()

    def get_asl(self) -> int:
        server_level = self.char_sheet.get('B1')
        return int(server_level.first())

    def get_tier(self) -> int:
        return bisect.bisect(TIERS, self.get_asl())

    def get_shop_tier(self) -> int:
        return bisect.bisect(SHOP_TIERS, self.get_asl())
