import discord
import logging
import re
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
global USERLIST
global ASL
global XPLIST


def merge(list1, list2):
    logging.info(f'{list1}')
    logging.info(f'{list2}')
    return [(list1[i], list2[i]) for i in range(0, len(list1))]


def updateUserlist():
    RENDER_OPTION = "UNFORMATTED_VALUE"
    LIST_RANGE = 'Characters!A3:A'
    USERLIST = sheet.get(SPREADSHEET_ID, LIST_RANGE, RENDER_OPTION)
    USERLIST = USERLIST['values']
    return USERLIST


def updateASL():
    RENDER_OPTION = "UNFORMATTED_VALUE"
    ASL_RANGE = 'Characters!B1'
    ASL = sheet.get(SPREADSHEET_ID, ASL_RANGE, RENDER_OPTION)
    ASL = int(ASL['values'][0][0])
    return ASL


def updateXPlist():
    RENDER_OPTION = "FORMATTED_VALUE"
    XPLIST_RANGE = 'Characters!H3:H'
    xplist = sheet.get(SPREADSHEET_ID, XPLIST_RANGE, RENDER_OPTION)
    xplist = xplist['values']
    USERLIST = updateUserlist()
    return merge(USERLIST, xplist)


def getCL(id):
    IDINDEX = USERLIST.index(id)
    character_level = XPLIST[IDINDEX][1][0]
    return 1 + int((int(character_level) / 1000))


USERLIST = updateUserlist()
XPLIST = updateXPlist()
ASL = updateASL()
CL = getCL(['286360249659817984'])

print(f'XPLIST: {XPLIST}')
print(f'USERLIST: {USERLIST}')
print(f'ASL: {ASL}')
print(f'CL: {CL}')


class mgmt(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    # @commands.check(is_tracker)
    async def level(self, ctx):
        XPLIST_RANGE = 'Characters!H3:H'
        USERLIST = updateUserlist()
        RENDER_OPTION = "UNFORMATTED_VALUE"
        XPLIST = sheet.get(SPREADSHEET_ID, XPLIST_RANGE, RENDER_OPTION)
        XPLIST = XPLIST['values']
        XPLIST = merge(USERLIST, XPLIST)
        con = True
        xpcheck = True
        num = 0
        global nameCheck
        nameCheck = True
        if user_has_role(self, TRACKERS_ROLE, ctx):
            RANGE_NAME = ''
            msg = ctx.message.content[7:]
            result = [x.strip() for x in msg.split('.')]
            for i in result:
                if num == 0:
                    i = re.sub(r'\D+', '', i)
                    logging.info(f'{i}')
                    if [i] not in USERLIST:
                        logging.info(f'{nameCheck}')
                        nameCheck = False
                        break
                    else:
                        INDEX = USERLIST.index([i])
                        logging.info(f'{INDEX}')
                        CURRENTXPLIST = [x[1] for x in XPLIST]
                        logging.info(f'{CURRENTXPLIST}')
                        CURRENTXP = CURRENTXPLIST[INDEX]
                        logging.info(f'{CURRENTXP}')
                        if int(CURRENTXP[0]) > 2000:
                            xpcheck = False
                            break
                        elif int(CURRENTXP[0]) < 2000:
                            NEWXP = int(CURRENTXP[0]) + 1000
                        else:
                            NEWXP = 1000
                        DATA = []
                        DATA.append([NEWXP])
                        logging.info(f'{NEWXP}')
                        INSERT_RANGE = 'Characters!H' + str(INDEX + 3)
                        logging.info(f'{INSERT_RANGE}')
                        sheet.set(SPREADSHEET_ID, INSERT_RANGE, DATA, "COLUMNS")
                        await ctx.message.channel.send(msg + ' - level up submitted!')
            if nameCheck == False:
                await ctx.message.channel.send('Error: The @Name (1) was entered incorrectly. Please try again.')
            elif xpcheck == False:
                await ctx.message.channel.send('Error: The targeted player has over 2000 XP. Please enter manually.')
        else:
            await ctx.message.channel.send('Naughty Naughty ' + ctx.message.author.name)

    @commands.command()
    async def get(self, ctx):
        msg = ctx.message.content[5:]
        target = ''
        if len(msg) == 0:  # Get for the user sending the message
            target = [str(ctx.author.id)]
        elif len(msg.split()) == 1:  # Get for some other user
            target = [re.sub(r'\D+', '', msg)]

        if target in USERLIST:
            IN_RANGE_NAME = 'Bot Staging!A4'
            OUT_RANGE_NAME = 'Bot Staging!A9:B17'
            RENDER_OPTION = "UNFORMATTED_VALUE"
            values = [target]
            sheet.set(BOT_SPREADSHEET_ID, IN_RANGE_NAME, values, "COLUMNS")
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
    async def log_alt(self, ctx):
        command_data = []
        display_errors = []
        global USERLIST
        if not user_has_role(self, TRACKERS_ROLE, ctx):  # >log command requires Tracker role
            await ctx.message.channel.send('Naughty Naughty ' + ctx.message.author.name)
            return

        RANGE_NAME = 'Log!A2'
        msg = ctx.message.content[5:]
        log_args = [x.strip() for x in msg.split('.')]
        print(f'log_args: {log_args}')

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
            if [target_id] not in USERLIST:
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
            id_obj = [str(ctx.message.author.id)]  # Because the sheet formatting has to be a little extra
            command_data.append([getCL(id_obj)])
            command_data.append([ASL])
            print(f'DATA: {command_data}')  # TODO: Turn this into a proper logging statement
            sheet.add(SPREADSHEET_ID, RANGE_NAME, command_data, "COLUMNS")
            await ctx.message.channel.send(msg + ' - submitted by ' + ctx.author.nick)
        await ctx.message.delete()


    @commands.command()
    # @commands.check(is_tracker)
    async def log(self, ctx):
        command_data = []
        display_errors = []
        global USERLIST
        if not user_has_role(self, TRACKERS_ROLE, ctx):  # >log command requires Tracker role
            await ctx.message.channel.send('Naughty Naughty ' + ctx.message.author.name)
            return

        RANGE_NAME = 'Log!A2'
        FIELDS = 6  # Amount of fields/cells
        msg = ctx.message.content[5:]

        log_args = [x.strip() for x in msg.split('.')]
        if 2 <= len(log_args) <= FIELDS:

            # Start off by logging the user submitting the message and the date/time
            command_data.append([ctx.message.author.name])
            command_data.append([str(ctx.message.created_at)])

            # Get the user targeted by the log command
            target_name = re.sub(r'\D+', '', log_args[0])
            if [target_name] not in USERLIST:
                display_errors.append(NAME_ERROR)
            else:
                command_data.append([target_name])

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
                    try:
                        result = log_args[2].upper()
                        if result not in ['WIN', 'LOSS', 'HOST']:
                            display_errors.append(RESULT_ERROR)
                        else:
                            command_data.append([result])
                    except IndexError:
                        display_errors.append(MISSING_FIELD_ERROR)

                # Handle SHOP/SHOPKEEP
                # To-Do: Deprecate 'SHOPKEEP'. Nobody uses it.
                elif activity in ['SHOP', 'SHOPKEEP']:
                    try:
                        cost = re.sub(r'\D+', '', log_args[2])
                        if cost == '':
                            display_errors.append(NUMBER_ERROR)
                        else:
                            command_data.append([cost])
                    except IndexError:
                        display_errors.append(MISSING_FIELD_ERROR)

                # Handle BUY/SELL
                elif activity in ['BUY', 'SELL']:
                    try:
                        item_name = log_args[2]
                        cost = re.sub(r'\D+', '', log_args[3])
                        if cost == '':
                            display_errors.append(NUMBER_ERROR)
                        else:
                            command_data.append([item_name])
                            command_data.append([cost])
                    except IndexError:
                        display_errors.append(MISSING_FIELD_ERROR)

                # Handle QUEST/ACTIVITY/ADVENTURE, as well as BONUS/GLOBAL
                elif activity in ['QUEST', 'ACTIVITY', 'ADVENTURE', 'BONUS', 'GLOBAL']:
                    try:
                        activity_name = log_args[2].upper()
                        gp = re.sub(r'\D+', '', log_args[3])
                        xp = re.sub(r'\D+', '', log_args[4])
                        if xp == '' or gp == '':
                            display_errors.append(NUMBER_ERROR)
                        else:
                            command_data.append([activity_name])
                            command_data.append([gp])
                            command_data.append([xp])
                    except IndexError:
                        display_errors.append(MISSING_FIELD_ERROR)
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
            id_obj = [str(ctx.message.author.id)]  # Because the sheet formatting has to be a little extra
            command_data.append([getCL(id_obj)])
            command_data.append([ASL])
            print('DATA: ' + f'{command_data}')  # TODO: Turn this into a proper logging statement
            sheet.add(SPREADSHEET_ID, RANGE_NAME, command_data, "COLUMNS")
            await ctx.message.channel.send(msg + ' - submitted by ' + ctx.author.nick)
        await ctx.message.delete()

    @commands.command()
    # @commands.check(is_council)
    async def create(self, ctx):
        global USERLIST
        if user_has_role(self, COUNCIL_ROLE, ctx):
            USERLIST = updateUserlist()
            RANGE_NAME = 'Characters!A' + str(len(USERLIST) + 3)
            XP_RANGE = 'Characters!H' + str(len(USERLIST) + 3)
            msg = ctx.message.content[8:]
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
            USERLIST = updateUserlist()

        else:
            await ctx.message.delete()
            await ctx.message.channel.send('Naughty Naughty ' + ctx.message.author.name)
            return


def setup(bot):
    bot.add_cog(mgmt(bot))


def user_has_role(self, roleid, ctx):
    return roleid in map(lambda role: role.id, ctx.message.author.roles)

