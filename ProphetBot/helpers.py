from ProphetBot.constants import *
from datetime import datetime
import discord.utils
import gspread


def is_tracker(ctx):
    return {TRACKERS_ROLE, TRACKERS_ROLE_BP}.intersection(map(lambda role: role.id, ctx.message.author.roles))


def is_council(ctx):
    council_role = discord.utils.get(ctx.guild.roles, name='Council')
    return council_role in ctx.message.author.roles
    # return {COUNCIL_ROLE, COUNCIL_ROLE_BP}.intersection(map(lambda role: role.id, ctx.message.author.roles))


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
