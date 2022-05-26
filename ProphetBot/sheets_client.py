import bisect
import json
import os
from time import perf_counter
from typing import List, Optional, Dict, Any

import gspread
from gspread import Cell

from ProphetBot.constants import TIERS, SHOP_TIERS
from ProphetBot.models.sheets_objects import Character, LogEntry


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

    def get_all_characters(self) -> List | List[Character]:
        character_dicts = self.char_sheet.get_all_records(head=2, empty2zero=True)
        characters = [Character.from_dict(c) for c in character_dicts]
        return characters

    def get_character_from_id(self, discord_id: int | str) -> Optional[Character]:
        if isinstance(discord_id, int):
            discord_id = str(discord_id)
        header_row = '2:2'
        target_cell = self.char_sheet.find(discord_id, in_column=1)
        if not target_cell:
            return None

        user_row = str(target_cell.row) + ':' + str(target_cell.row)
        data = self.char_sheet.batch_get([header_row, user_row])
        data_dict = {k: v for k, v in zip(data[0][0], data[1][0])}

        return Character.from_dict(data_dict)

    def get_adventure_from_category_id(self, discord_id: int | str) -> Optional[Dict[str, Any]]:
        if isinstance(discord_id, int):
            discord_id = str(discord_id)
        header_row = '1:1'

        target_cell = self.adventures_sheet.find(discord_id, in_column=2)
        if not target_cell:
            return None

        adventure_row = str(target_cell.row) + ':' + str(target_cell.row)
        data = self.adventures_sheet.batch_get([header_row, adventure_row])

        return {k: v for k, v in zip(data[0][0], data[1][0])}

    def get_adventure_from_role_id(self, discord_id: int | str) -> Optional[Dict[str, Any]]:
        if isinstance(discord_id, int):
            discord_id = str(discord_id)
        header_row = '1:1'

        target_cell = self.adventures_sheet.find(discord_id, in_column=1)
        if not target_cell:
            return None

        adventure_row = str(target_cell.row) + ':' + str(target_cell.row)
        data = self.adventures_sheet.batch_get([header_row, adventure_row])

        return {k: v for k, v in zip(data[0][0], data[1][0])}

    def create_character(self, character: Character):
        """
        Adds a new character to the 'Characters' sheet in BPdia

        :param character: Character object representing a newly-created character
        """
        character_data = [
            str(character.player_id),
            character.name,
            character.faction,
            character.character_class,
            character.wealth,
            '',
            '',
            character.experience
        ]
        print(f"Appending new character to sheet with data {character_data}")
        self.char_sheet.append_row(character_data, value_input_option='USER_ENTERED',
                                   insert_data_option='INSERT_ROWS', table_range='A2')

    def log_activity(self, log_entry: LogEntry):
        """
        Logs a single activity to the BPdia Log worksheet

        :param log_entry: A LogEntry (or usually a subclass thereof) to be logged
        """

        log_data = log_entry.to_sheets_row()

        print(f"Logging activity with data {log_data}")
        self.log_sheet.append_row(log_data, value_input_option='USER_ENTERED',
                                  insert_data_option='INSERT_ROWS', table_range='A2')

    def log_activities(self, log_entries: List[LogEntry]):
        """
        Logs multiple activities to the BPdia Log worksheet. Gspread calls are expensive, so use this for 2+ logs.

        :param log_entries: A list of LogEntry (or usually a subclass thereof) to be logged
        """

        log_data = [entry.to_sheets_row() for entry in log_entries]

        print(f"Logging activity with data {log_data}")
        self.log_sheet.append_rows(log_data, value_input_option='USER_ENTERED',
                                   insert_data_option='INSERT_ROWS', table_range='A2')

    def update_faction(self, player_id: int, faction_name: str):
        player_cell: Cell = self.char_sheet.find(str(player_id), in_column=1)
        faction_cell: Cell = self.char_sheet.find("Faction", in_row=2)

        if player_cell is None or faction_cell is None:
            raise ValueError

        print(f"Updating cell [ {player_cell.row}:{faction_cell.col} ] to [ \"{faction_name}\" ]")
        self.char_sheet.update_cell(player_cell.row, faction_cell.col, faction_name)

    def update_reset_xp(self, player_id: int, new_xp: int):
        player_cell: Cell = self.char_sheet.find(str(player_id), in_column=1)
        reset_xp_cell: Cell = self.char_sheet.find("Reset XP", in_row=2)

        print(f"Updating cell [ {player_cell.row}:{reset_xp_cell.col} ] to [ \"{new_xp}\" ]")
        self.char_sheet.update_cell(player_cell.row, reset_xp_cell.col, new_xp)
