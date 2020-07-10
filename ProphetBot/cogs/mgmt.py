import discord
import logging
import re
from timeit import default_timer as timer
from ProphetBot.constants import *
from ProphetBot.localsettings import *
# from ProphetBot.cogs.helpers import *
from discord.ext import commands
import importlib.util
from texttable import Texttable

# NEVER COPY OVER THIS
# gloc = 'C:\\Users\\Nick\\ProphetBot\\cogs\\mod\\gsheet.py'
# gloc = 'D:\\OneDrive\\Scripts\\Public\\ProphetBot\\cogs\\mod\\gsheet.py'


spec = importlib.util.spec_from_file_location("gsheet", gloc)
foo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(foo)
sheet = foo.gsheet()
# SPREADSHEET_ID = '156aVcYNPLE2OAO8Ga78zmxciCrKIzCzXSn7-cQFbSMY'
# BOT_SPREADSHEET_ID = '1Hm-WthWv_kwBeUlB_ECzcltveasT7QwuWudk76v1uoQ'
# global USERLIST
# global ASL
# global XPLIST
global xpmap


# def merge(list1, list2):
#     logging.info(f'{list1}')
#     logging.info(f'{list2}')
#     return [(list1[i], list2[i]) for i in range(0, len(list1))]


# def updateUserlist():
#     RENDER_OPTION = "UNFORMATTED_VALUE"
#     LIST_RANGE = 'Characters!A3:A'
#     USERLIST = sheet.get(SPREADSHEET_ID, LIST_RANGE, RENDER_OPTION)
#     USERLIST = USERLIST['values']
#     return USERLIST


def updateASL():
    RENDER_OPTION = "UNFORMATTED_VALUE"
    ASL_RANGE = 'Characters!B1'
    ASL = sheet.get(SPREADSHEET_ID, ASL_RANGE, RENDER_OPTION)
    ASL = int(ASL['values'][0][0])
    return ASL


# def updateXPlist():
#     RENDER_OPTION = "FORMATTED_VALUE"
#     XPLIST_RANGE = 'Characters!H3:H'
#     xplist = sheet.get(SPREADSHEET_ID, XPLIST_RANGE, RENDER_OPTION)
#     xplist = xplist['values']
#     USERLIST = updateUserlist()
#     return merge(USERLIST, xplist)


def build_user_map():
    XPLIST_RANGE = 'Characters!H3:H'
    xplist = sheet.get(SPREADSHEET_ID, XPLIST_RANGE, "FORMATTED_VALUE")
    xplist = xplist['values']
    USERLIST_RANGE = 'Characters!A3:A'
    userlist = sheet.get(SPREADSHEET_ID, USERLIST_RANGE, "UNFORMATTED_VALUE")
    # userlist_ranges = userlist['range']
    userlist = userlist['values']
    # print(f'userlist values: {userlist}')
    # print(f'userlist ranges: {userlist_ranges}')
    return {  # Using fancy dictionary comprehension to make the dict
        str(key[0]): value[0] for key, value in zip(userlist, xplist)
    }


def getCL(charid, xpmap):
    character_level = xpmap[charid]
    # print(f'ID: {charid}, Level (XP): {character_level}')
    return 1 + int((int(character_level) / 1000))


class mgmt(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    # @commands.check(is_tracker)
    async def level(self, ctx):
        user_map = build_user_map()
        if not user_has_role(self, TRACKERS_ROLE, ctx):
            await ctx.message.channel.send('Naughty Naughty ' + ctx.message.author.name)

        msg = ctx.message.content[7:]
        result = [x.strip() for x in msg.split('.')]
        print(f'{str(ctx.message.created_at)} - Incoming \'Level\' command from {ctx.message.author.name}'
              f'. Args: {result}')
        if len(result) != 1:
            # Error case
            await ctx.message.channel.send(INPUT_ERROR)
            return

        target = re.sub(r'\D+', '', result[0])
        if target not in user_map:
            await ctx.message.channel.send(NAME_ERROR)
            return

        if (targetXP := int(user_map[target])) > 2000:
            await ctx.message.channel.send('Error: The targeted player has over 2000 XP. Please enter manually.')
            return
        elif targetXP < 2000:
            newXP = targetXP + 1000
        else:
            newXP = 1000

        DATA = [[newXP]]
        logging.info(f'New XP for target {target}: {newXP}')
        index = list(user_map.keys()).index(target)  # Dicts preserve order in Python 3. Fancy.
        INSERT_RANGE = 'Characters!H' + str(index + 3)  # Could find the index in this same line, but that's messy
        logging.info(f'Insert Range: {INSERT_RANGE}')
        sheet.set(SPREADSHEET_ID, INSERT_RANGE, DATA, "COLUMNS")
        await ctx.message.channel.send(msg + ' - level up submitted by ' + ctx.author.name)

    @commands.command()
    async def get(self, ctx):
        msg = ctx.message.content[5:]
        get_args = [x.strip() for x in msg.split('.')]
        print(f'Incoming \'Get\' command. Args: {get_args}')
        target = ''
        user_map = build_user_map()
        if len(msg) == 0:  # Get for the user sending the message
            target = str(ctx.author.id)
        elif len(msg.split()) == 1:  # Get for some other user
            target = re.sub(r'\D+', '', msg)

        if target in user_map:
            IN_RANGE_NAME = 'Bot Staging!A4'
            OUT_RANGE_NAME = 'Bot Staging!A9:B17'
            RENDER_OPTION = "UNFORMATTED_VALUE"
            values = [target]
            print(f'values: {values}')
            sheet.set(BOT_SPREADSHEET_ID, IN_RANGE_NAME, [values], "COLUMNS")
            data_out = sheet.get(BOT_SPREADSHEET_ID, OUT_RANGE_NAME, RENDER_OPTION)
            send_data = data_out['values']
            logging.info(f'{send_data}')
            t = Texttable()
            t.set_cols_align(["l", "r"])
            t.set_cols_valign(["m", "m"])
            t.add_rows(send_data)
            get_message = t.draw()

            await ctx.send("`" + get_message + "`")
        else:
            await ctx.send(
                "'" + msg + "' is not a valid input... >get for your own stats, >get @name for someone else.")
        await ctx.message.delete()
        print("success")

    @commands.command()
    # @commands.check(is_council)
    async def weekly(self, ctx):
        # Command to process the weekly reset
        if user_has_role(self, COUNCIL_ROLE, ctx):
            await ctx.channel.send("`PROCESSING WEEKLY RESET`")
            RENDER_OPTION = "UNFORMATTED_VALUE"
            RANGE_NAME_XP_PEND = 'Characters!I3:I'
            RANGE_NAME_XP_TOTAL = 'Characters!H3:H'
            RANGE_NAME_GP_PEND = 'Characters!F3:F'
            RANGE_NAME_GP_TOTAL = 'Characters!E3:E'
            gp_pend = sheet.get(SPREADSHEET_ID, RANGE_NAME_GP_PEND, RENDER_OPTION)
            xp_pend = sheet.get(SPREADSHEET_ID, RANGE_NAME_XP_PEND, RENDER_OPTION)
            gp_total = gp_pend.get('values', {})
            xp_total = xp_pend.get('values', {})
            # print("GP PEND:" + f'{gp_pend}')
            # print("XP PEND:" + f'{xp_pend}')
            # print("GP TOTAL:" + f'{gp_total}')
            # print("XP TOTAL:" + f'{xp_total}')
            sheet.set(SPREADSHEET_ID, RANGE_NAME_GP_TOTAL, gp_total, "ROWS")
            sheet.set(SPREADSHEET_ID, RANGE_NAME_XP_TOTAL, xp_total, "ROWS")
            LOG_RANGE_IN = 'Log!A2:G500'
            LOG_RANGE_OUT = 'Archive Log!A2:G500'
            LOG_IN = sheet.get(SPREADSHEET_ID, LOG_RANGE_IN, RENDER_OPTION)
            LOG_OUT = LOG_IN.get('values', {})
            sheet.add(SPREADSHEET_ID, LOG_RANGE_OUT, LOG_OUT, "ROWS")
            sheet.clear(SPREADSHEET_ID, LOG_RANGE_IN)
            await ctx.message.delete()
            await ctx.channel.send("`WEEKLY RESET HAS OCCURRED.`")
        else:
            await ctx.message.delete()
            await ctx.message.channel.send('Naughty Naughty ' + ctx.message.author.name)
            return

    @commands.command()
    # @commands.check(is_tracker)
    async def log(self, ctx):
        start = timer()
        global xpmap
        command_data = []
        display_errors = []
        # usermap = build_xpmap()
        usermap = xpmap
        if not user_has_role(self, TRACKERS_ROLE, ctx):  # >log command requires Tracker role
            await ctx.message.channel.send('Naughty Naughty ' + ctx.message.author.name)
            return

        RANGE_NAME = 'Log!A2'
        msg = ctx.message.content[5:]
        log_args = [x.strip() for x in msg.split('.')]
        print(f'{str(ctx.message.created_at)} - Incoming \'Log\' command from {ctx.message.author.name}'
              f'. Args: {log_args}')  # TODO: This should log actual time, not message time

        # types: list of either 'int', 'str', or 'str_upper'
        def parse_activity(*types):
            num_args = len(types)
            offset = 2  # First two index positions are always spoken for
            # check for too few arguments
            if len(log_args) < num_args + offset:
                display_errors.append(MISSING_FIELD_ERROR)

            for i in range(num_args):
                arg = log_args[offset + i]
                if types[i] == 'int':
                    try:
                        arg = int(arg.lstrip('0'))
                    except ValueError:
                        display_errors.append(NUMBER_ERROR)
                elif types[i] == 'str':
                    arg = str(arg)
                elif types[i] == 'str_upper':
                    arg = str(arg).upper()
                else:
                    raise Exception('Incorrect argument type in `types`')

                command_data.append([arg])

        if 2 <= len(log_args):

            # Start off by logging the user submitting the message and the date/time
            command_data.append([ctx.message.author.name])
            command_data.append([str(ctx.message.created_at)])

            # Get the user targeted by the log command
            target_id = re.sub(r'\D+', '', log_args[0])
            if target_id not in usermap:
                display_errors.append(NAME_ERROR)
            else:
                command_data.append([target_id])

            # Get the activity type being logged
            activity = log_args[1].upper()
            if activity not in ACTIVITY_TYPES:  # Grabbing ACTIVITY_TYPES from constants.py
                display_errors.append(ACTIVITY_ERROR)
            else:
                command_data.append([activity])

            if len(display_errors) == 0:
                # Handle RP
                if activity in ['RP', 'MOD', 'ADMIN']:
                    if len(log_args) > 2:
                        display_errors.append(INPUT_ERROR)

                # Handle PIT/ARENA
                elif activity in ['ARENA', 'PIT']:
                    if len(log_args) < 3 or log_args[2].upper() not in ['WIN', 'LOSS', 'HOST']:
                        display_errors.append(RESULT_ERROR)
                    else:
                        parse_activity('str_upper')

                # Handle SHOP/SHOPKEEP
                # To-Do: Deprecate 'SHOPKEEP'. Nobody uses it.
                elif activity in ['SHOP', 'SHOPKEEP']:
                    parse_activity('int')

                # Handle BUY/SELL
                elif activity in ['BUY', 'SELL']:
                    parse_activity('str', 'int')

                # Handle QUEST/ACTIVITY/ADVENTURE, as well as BONUS/GLOBAL
                elif activity in ['QUEST', 'ACTIVITY', 'ADVENTURE', 'BONUS', 'GLOBAL']:
                    parse_activity('str', 'int', 'int')

                else:
                    display_errors.append('How did you even get here?')
        else:
            display_errors.append('Error: There must be 2-5 fields entered.')

        if len(display_errors) > 0:
            for error in display_errors:
                await ctx.message.channel.send(error)
        else:
            while len(command_data) < 7:
                command_data.append([''])  # Pad until CL and ASL
            target_id = re.sub(r'\D+', '', log_args[0])
            xpmap = build_user_map()
            command_data.append([getCL(target_id, xpmap)])  # Because the sheet formatting has to be a little extra
            command_data.append([updateASL()])
            print(f'DATA: {command_data}')  # TODO: Turn this into a proper logging statement
            sheet.add(SPREADSHEET_ID, 'Log!A2', command_data, "COLUMNS")
            stop = timer()
            print(f'Elapsed time: {stop - start}')
            await ctx.message.channel.send(msg + ' - submitted by ' + ctx.author.nick)
        await ctx.message.delete()

    @commands.command()
    # @commands.check(is_council)
    async def create(self, ctx):
        # global USERLIST
        if user_has_role(self, COUNCIL_ROLE, ctx):
            USERLIST = build_user_map()  # TODO: Test this
            RANGE_NAME = 'Characters!A' + str(len(USERLIST) + 3)
            XP_RANGE = 'Characters!H' + str(len(USERLIST) + 3)
            msg = ctx.message.content[8:]
            create_args = [x.strip() for x in msg.split('.')]
            print(f'Incoming \'Create\' command. Args: {create_args}')
            result = [x.strip() for x in msg.split('.')]
            print(f'{result}')
            print(f'{RANGE_NAME}')

            DATA = []
            for i in result:
                if i.startswith("<"):
                    i = re.sub(r'\D+', '', i)
                DATA.append([i])

            DATA2 = []
            DATA2.append(['0'])
            sheet.set(SPREADSHEET_ID, RANGE_NAME, DATA, "COLUMNS")
            sheet.set(SPREADSHEET_ID, XP_RANGE, DATA2, "COLUMNS")
            print(f'{DATA}')
            await ctx.message.delete()
            await ctx.message.channel.send(ctx.message.content[8:] + ' - submitted!')
            # USERLIST = updateUserlist()

        else:
            await ctx.message.delete()
            await ctx.message.channel.send('Naughty Naughty ' + ctx.message.author.name)
            return


def setup(bot):
    global xpmap
    bot.add_cog(mgmt(bot))

    # USERLIST = updateUserlist()
    # XPLIST = updateXPlist()
    ASL = updateASL()
    xpmap = build_user_map()
    CL = getCL('286360249659817984', xpmap)

    # print(f'XPLIST: {XPLIST}')
    # print(f'USERLIST: {USERLIST}')
    print(f'XP Map: {xpmap}')
    print(f'ASL: {ASL}')
    print(f'CL: {CL}')


def user_has_role(self, roleid, ctx):
    return roleid in map(lambda role: role.id, ctx.message.author.roles)

