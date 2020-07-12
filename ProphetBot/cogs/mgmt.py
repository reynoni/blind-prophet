import discord
import logging
import re
from timeit import default_timer as timer
from ProphetBot.constants import *
from ProphetBot.localsettings import *
from ProphetBot.cogs.mod.gsheet import gsheet
from ProphetBot.helpers import *  # Not needed until we get decorator checks working
from discord.ext import commands
from texttable import Texttable


def setup(bot):
    bot.add_cog(mgmt(bot))


def user_has_role(roleid, ctx):
    return roleid in map(lambda role: role.id, ctx.message.author.roles)


class mgmt(commands.Cog):

    def __init__(self, bot):
        # Setting up some objects
        self.bot = bot
        self.sheet = gsheet()
        self.ASL = self.updateASL()
        self.user_map = self.build_user_map()

        print(f'User Map: {self.user_map}')
        print(f'ASL: {self.ASL}')

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.message.channel.send('Naughty Naughty ' + ctx.message.author.name)
            return

    @commands.command()
    @commands.check(is_tracker)
    async def level(self, ctx):
        self.user_map = self.build_user_map()
        msg = ctx.message.content[7:]

        result = [x.strip() for x in msg.split('.')]
        print(f'{str(ctx.message.created_at)} - Incoming \'Level\' command from {ctx.message.author.name}'
              f'. Args: {result}')
        if len(result) != 1:
            # Error case
            await ctx.message.channel.send(INPUT_ERROR)
            return

        target = re.sub(r'\D+', '', result[0])
        if target not in self.user_map:
            await ctx.message.channel.send(NAME_ERROR)
            return

        if (targetXP := int(self.user_map[target])) > 2000:
            await ctx.message.channel.send('Error: The targeted player has over 2000 XP. Please enter manually.')
            return
        elif targetXP < 2000:
            newXP = targetXP + 1000
        else:
            newXP = 1000

        insert_data = [[newXP]]
        logging.info(f'New XP for target {target}: {newXP}')
        index = list(self.user_map.keys()).index(target)  # Dicts preserve order in Python 3. Fancy.
        insert_range = 'Characters!H' + str(index + 3)  # Could find the index in this same line, but that's messy
        logging.info(f'Insert Range: {insert_range}')
        self.sheet.set(SPREADSHEET_ID, insert_range, insert_data, "COLUMNS")
        await ctx.message.channel.send(msg + ' - level up submitted by ' + ctx.author.name)

    @commands.command()
    async def update(self, ctx):
        self.ASL = self.updateASL()
        self.user_map = self.build_user_map()
        await ctx.message.channel.send('User Map and ASL updated by ' + ctx.author.nick)
        await ctx.message.delete()

    @commands.command()
    async def get(self, ctx):
        msg = ctx.message.content[5:]
        get_args = [x.strip() for x in msg.split('.')]
        print(f'Incoming \'Get\' command. Args: {get_args}')
        target = ''
        self.user_map = self.build_user_map()
        if len(msg) == 0:  # Get for the user sending the message
            target = str(ctx.author.id)
        elif len(msg.split()) == 1:  # Get for some other user
            target = re.sub(r'\D+', '', msg)

        if target in self.user_map:
            IN_RANGE_NAME = 'Bot Staging!A4'
            OUT_RANGE_NAME = 'Bot Staging!A9:B17'
            RENDER_OPTION = "UNFORMATTED_VALUE"
            values = [target]
            print(f'values: {values}')
            self.sheet.set(BOT_SPREADSHEET_ID, IN_RANGE_NAME, [values], "COLUMNS")
            data_out = self.sheet.get(BOT_SPREADSHEET_ID, OUT_RANGE_NAME, RENDER_OPTION)
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
    @commands.check(is_council)
    async def weekly(self, ctx):
        # Command to process the weekly reset
        await ctx.channel.send("`PROCESSING WEEKLY RESET`")

        # Process pending GP/XP
        RENDER_OPTION = "UNFORMATTED_VALUE"
        RANGE_NAME_XP_PEND = 'Characters!I3:I'
        RANGE_NAME_XP_TOTAL = 'Characters!H3:H'
        RANGE_NAME_GP_PEND = 'Characters!F3:F'
        RANGE_NAME_GP_TOTAL = 'Characters!E3:E'
        gp_pend = self.sheet.get(SPREADSHEET_ID, RANGE_NAME_GP_PEND, RENDER_OPTION)
        xp_pend = self.sheet.get(SPREADSHEET_ID, RANGE_NAME_XP_PEND, RENDER_OPTION)
        gp_total = gp_pend.get('values', {})
        xp_total = xp_pend.get('values', {})
        self.sheet.set(SPREADSHEET_ID, RANGE_NAME_GP_TOTAL, gp_total, "ROWS")
        self.sheet.set(SPREADSHEET_ID, RANGE_NAME_XP_TOTAL, xp_total, "ROWS")

        # Archive old log entries
        LOG_RANGE_IN = 'Log!A2:G500'
        LOG_RANGE_OUT = 'Archive Log!A2:G500'
        LOG_IN = self.sheet.get(SPREADSHEET_ID, LOG_RANGE_IN, RENDER_OPTION)
        LOG_OUT = LOG_IN.get('values', {})
        self.sheet.add(SPREADSHEET_ID, LOG_RANGE_OUT, LOG_OUT, "ROWS")
        self.sheet.clear(SPREADSHEET_ID, LOG_RANGE_IN)

        await ctx.message.delete()
        await ctx.channel.send("`WEEKLY RESET HAS OCCURRED.`")

    @commands.command()
    @commands.check(is_tracker)
    async def log(self, ctx):
        start = timer()
        command_data = []
        display_errors = []

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
            if target_id not in self.user_map:
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
            command_data.append([self.get_CL(target_id)])  # Because the sheet formatting has to be a little extra
            command_data.append([self.updateASL()])
            print(f'DATA: {command_data}')  # TODO: Turn this into a proper logging statement
            self.sheet.add(SPREADSHEET_ID, 'Log!A2', command_data, "COLUMNS")
            stop = timer()
            print(f'Elapsed time: {stop - start}')
            await ctx.message.channel.send(msg + ' - submitted by ' + ctx.author.nick)
        await ctx.message.delete()

    @commands.command()
    @commands.check(is_council)
    async def create(self, ctx):
        RANGE_NAME = 'Characters!A' + str(len(self.user_map.keys()) + 3)
        XP_RANGE = 'Characters!H' + str(len(self.user_map.keys()) + 3)
        msg = ctx.message.content[8:]
        args = [x.strip() for x in msg.split('.')]
        print(f'Incoming \'Create\' command. Args: {args}')
        # print(f'{RANGE_NAME}')

        if not len(args) == 5:  # [@user, name, faction, class, starting gp]
            # Error case
            await ctx.message.channel.send(INPUT_ERROR)
            return

        user_id = re.sub(r'\D+', '', args.pop(0))
        DATA = [[user_id]]
        for i in args:
            DATA.append([i])

        reset_xp = [['0']]
        self.sheet.set(SPREADSHEET_ID, RANGE_NAME, DATA, "COLUMNS")
        self.sheet.set(SPREADSHEET_ID, XP_RANGE, reset_xp, "COLUMNS")
        print(f'{DATA}')
        await ctx.message.delete()
        await ctx.message.channel.send(ctx.message.content[8:] + ' - submitted!')
        self.user_map = self.build_user_map()

    # --------------------------- #
    # Helper functions
    # --------------------------- #
    @level.error
    @weekly.error
    @log.error
    @create.error
    async def error_handler(self, ctx, error):  # TODO: Move this check to a universal on_command_error() override
        if isinstance(error, commands.CheckFailure):
            await ctx.message.channel.send('Naughty Naughty ' + ctx.message.author.name)
            return

    def updateASL(self):
        ASL_RANGE = 'Characters!B1'
        server_level = self.sheet.get(SPREADSHEET_ID, ASL_RANGE, "UNFORMATTED_VALUE")
        server_level = int(server_level['values'][0][0])
        return server_level

    def build_user_map(self):
        XPLIST_RANGE = 'Characters!H3:H'
        USERLIST_RANGE = 'Characters!A3:A'
        xp_list = self.sheet.get(SPREADSHEET_ID, XPLIST_RANGE, "FORMATTED_VALUE")
        user_list = self.sheet.get(SPREADSHEET_ID, USERLIST_RANGE, "UNFORMATTED_VALUE")
        user_list = user_list['values']
        xp_list = xp_list['values']

        return {  # Using fancy dictionary comprehension to make the dict
            str(key[0]): value[0] for key, value in zip(user_list, xp_list)
        }

    def get_CL(self, charid):
        character_level = self.user_map[charid]
        # print(f'ID: {charid}, Level (XP): {character_level}')
        return 1 + int((int(character_level) / 1000))
