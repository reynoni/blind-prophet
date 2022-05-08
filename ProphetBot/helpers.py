from typing import List

from ProphetBot.constants import *
from ProphetBot.models.sheets_objects import Character
from datetime import datetime
import discord.utils
import gspread


def filter_characters_by_ids(characters_list: List[Character], ids: List[int]) -> List[Character] | None:
    """
    Filters a list of Characters by discord ids

    :param characters_list: The List of Characters to be filtered
    :param ids: List of discord ids to filter by
    :return: The filtered list of Characters or None if no characters found
    """
    filtered = list(filter(lambda c: c.player_id in ids, characters_list))
    return filtered if len(filtered) > 0 else None


def is_admin(ctx):
    return ctx.author.id in ADMIN_USERS


def get_asl(char_sheet):
    try:
        server_level = char_sheet.get('B1')
        return int(server_level[0][0])
    except gspread.exceptions.APIError as E:
        print(E)


def get_user_map(char_sheet):
    userlist_range = 'A3:A'
    xplist_range = 'I3:I'
    try:
        results = char_sheet.batch_get([userlist_range, xplist_range])
        return {  # Using "fancy" dictionary comprehension to make the dict
            str(key[0]): int(value[0]) for key, value in zip(results[0], results[1])
        }
    except gspread.exceptions.APIError as E:
        print(E)


def get_cl(char_xp):
    return 1 + int((int(char_xp) / 1000))


def sheetstr(time: datetime) -> str:
    return time.strftime('%d/%m/%Y %H:%M:%S')
