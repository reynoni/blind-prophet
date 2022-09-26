import itertools
import math
from datetime import datetime
from typing import List, Any

import discord
import gspread
import numpy as np
from discord import ApplicationContext
from sqlalchemy.util import asyncio

from ProphetBot.constants import *
from ProphetBot.models.sheets_objects import Character


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


def split_dict(d):
    n = len(d) // 2  # length of smaller half
    i = iter(d.items())  # alternatively, i = d.iteritems() works in Python 2

    d1 = dict(itertools.islice(i, n))  # grab first n items
    d2 = dict(i)  # grab the rest

    return d1, d2


def split_evenly(input_list: List[Any], max_channels: int = 10) -> List[List[Any]]:
    n = math.ceil(len(input_list) / max_channels)
    arrays = np.array_split(input_list, n)
    return [a.tolist() for a in arrays]


def ceildiv(a, b):
    return -(a // -b)


def calc_amt(base: int, pmod: str = None, hostmod: str = None) -> int:
    if pmod is None:
        pmult = 0
        pmod = 'Low'
    else:
        pmult = GLOBAL_MOD_MAP[pmod]

    if hostmod is None:
        hadd = 0
    elif hostmod.upper() == "PARTICIPATING":
        hadd = 100
    elif hostmod.upper() == "HOSTING ONLY":
        hadd = (base * .75) + 100
        pmult = 0

    max = GLOBAL_MOD_MAX_MAP[pmod]
    amt = round((base * pmult))

    if amt > max:
        amt = max
    amt += hadd
    return amt


def get_positivity(string):
    if isinstance(string, bool):  # oi!
        return string
    lowered = string.lower()
    if lowered in ("yes", "y", "true", "t", "1", "enable", "on"):
        return True
    elif lowered in ("no", "n", "false", "f", "0", "disable", "off"):
        return False
    else:
        return None


def auth_and_chan(ctx):
    """Message check: same author and channel"""

    def chk(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    return chk


async def confirm(ctx, message, delete_msgs=False, response_check=get_positivity):
    """
    Confirms whether a user wants to take an action.
    :rtype: bool|None
    :param ctx: The current Context.
    :param message: The message for the user to confirm.
    :param delete_msgs: Whether to delete the messages.
    :param response_check: A function (str) -> bool that returns whether a given reply is a valid response.
    :type response_check: (str) -> bool
    :return: Whether the user confirmed or not. None if no reply was recieved
    """
    msg = await ctx.channel.send(message)
    try:
        reply = await ctx.bot.wait_for("message", timeout=30, check=auth_and_chan(ctx))
    except asyncio.TimeoutError:
        return None
    reply_bool = response_check(reply.content) if reply is not None else None
    if delete_msgs:
        try:
            await msg.delete()
            await reply.delete()
        except:
            pass
    return reply_bool
