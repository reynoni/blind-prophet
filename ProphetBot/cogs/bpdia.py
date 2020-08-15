import logging
import re
from gspread import *
from timeit import default_timer as timer
from ProphetBot.constants import *
from ProphetBot.localsettings import *
from ProphetBot.cogs.mod.gsheet import gsheet
from ProphetBot.helpers import *  # Not needed until we get decorator checks working
from discord.ext import commands
from texttable import Texttable


def setup(bot):
    bot.add_cog(BPdia(bot))


def build_table(data, level):
    character_data = []
    character_data.append(['Name', str(data[1])])
    character_data.append(['Class', str(data[3])])
    character_data.append(['Faction', str(data[2])])
    character_data.append(['Level', data[6]])
    character_data.append(['Wealth', data[5]])
    character_data.append(['Experience', data[8]])

    if level > 3:
        character_data.append(['Div GP', str(data[21]) + '/' + str(data[22])])
        character_data.append(['Div XP', str(data[23]) + '/' + str(data[24])])
        character_data.append(['ASL Mod', str(data[9])])
    else:
        needed_arena = 1 if level == 1 else 2
        needed_rp = 1 if level == 1 else 2
        num_arena = int(data[26]) if level == 1 else (int(data[30]) + int(data[31]))
        num_rp =    int(data[25]) if level == 1 else (int(data[28]) + int(data[29]))
        num_pit =   int(data[27]) if level == 1 else int(data[32])
        character_data.append(['RP', str(num_rp) + '/' + str(needed_rp)])
        character_data.append(['Arena', str(num_arena) + '/' + str(needed_arena)])
        character_data.append(['Pit', str(num_pit) + '/1'])

    table = Texttable()
    table.set_cols_align(["l", "r"])
    table.set_cols_valign(["m", "m"])
    table.add_rows(character_data)
    return table.draw()


class BPdia(commands.Cog):

    def __init__(self, bot):
        # Setting up some objects
        self.bot = bot
        self.sheet = gsheet()
        self.ASL = self.update_asl()
        self.user_map = self.build_user_map()

        print(f'Cog \'BPdia\' loaded')
        print(f'User Map: {self.user_map}')
        print(f'ASL: {self.ASL}')

    @commands.command(brief='- Provides a link to the public BPdia sheet')
    async def sheet(self, ctx):
        link = '<https://docs.google.com/spreadsheets/d/' + '1Ps6SWbnlshtJ33Yf30_1e0RkwXpaPy0YVFYaiETnbns' + '/>'
        await ctx.message.channel.send(f'The BPdia public sheet can be found at:\n{link}')
        await ctx.message.delete()

    @commands.command()
    @commands.check(is_admin)
    async def expiry(self, ctx):
        await ctx.message.channel.send(f'The Google token expires at {self.sheet.get_token_expiry()}')
        await ctx.message.delete()

    @commands.command(brief='- Manually levels initiates',
                      help=LEVEL_HELP)
    @commands.check(is_tracker)
    async def level(self, ctx):
        msg = ctx.message.content[7:]
        self.user_map = self.build_user_map()
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
            new_xp = targetXP + 1000
        else:
            new_xp = 1000

        insert_data = [[new_xp]]
        # logging.info(f'New XP for target {target}: {new_xp}')
        index = list(self.user_map.keys()).index(target)  # Dicts preserve order in Python 3. Fancy.
        insert_range = 'Characters!H' + str(index + 3)  # Could find the index in this same line, but that's messy
        # logging.info(f'Insert Range: {insert_range}')
        self.sheet.set(SPREADSHEET_ID, insert_range, insert_data, "COLUMNS")
        await ctx.message.channel.send(msg + ' - level submitted by ' + ctx.author.nick)
        await ctx.message.delete()

    # @commands.command(brief='- Updates ASL and user XP map', help=UPDATE_HELP)
    # async def update(self, ctx):
    #     self.ASL = self.update_asl()
    #     self.user_map = self.build_user_map()
    #     await ctx.message.channel.send('User Map and ASL updated by ' + ctx.author.nick)
    #     await ctx.message.delete()

    @commands.command(brief='- Displays character information for a user',
                      help=GET_HELP)
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

        if target not in self.user_map:
            await ctx.send(
                "'" + msg + "' is not a valid input... >get for your own stats, >get @name for someone else.")
            return

        IN_RANGE_NAME = 'Bot Staging!A4'
        OUT_RANGE_NAME = 'Bot Staging!A9:B17'
        RENDER_OPTION = "UNFORMATTED_VALUE"
        values = [target]
        # print(f'values: {values}')
        self.sheet.set(BOT_SPREADSHEET_ID, IN_RANGE_NAME, [values], "COLUMNS")
        data_out = self.sheet.get(BOT_SPREADSHEET_ID, OUT_RANGE_NAME, RENDER_OPTION)
        send_data = data_out['values']
        logging.info(f'{send_data}')
        t = Texttable()
        t.set_cols_align(["l", "r"])
        t.set_cols_valign(["m", "m"])
        # print(f'send_data: {send_data}')
        t.add_rows(send_data)
        get_message = t.draw()

        await ctx.send("`" + get_message + "`")
        await ctx.message.delete()

    @commands.command(brief='- !EXPERIMENTAL! Displays character information for a user',
                      help=GET_HELP)
    async def get_alt(self, ctx, target=None):
        if not target:
            target = str(ctx.author.id)
        else:
            target = re.sub(r'\D+', '', target)
        print(f'Incoming \'Get_Alt\' command. Args: {target}')
        u_map = self.build_user_map()

        if target not in self.user_map:
            await ctx.send(
                "'" + target + "' is not a valid input... >get for your own stats, >get @name for someone else.")
            return

        index = list(u_map.keys()).index(target)  # Dicts preserve order in Python 3. Fancy.
        user_row = 'Characters!A' + str(index + 3) + ':AE' + str(index + 3)  # Probably shouldn't specify columns

        data = self.sheet.get(SPREADSHEET_ID, user_row, "FORMATTED_VALUE")
        data = data['values']
        print(f'get_alt data: {data}')

        table = build_table(data[0], self.get_cl(target))
        await ctx.send("`" + table + "`")
        await ctx.message.delete()

    @commands.command(brief='- Processes the weekly reset',
                      help=WEEKLY_HELP)
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
        LOG_RANGE_IN = 'Log!A2:I'
        LOG_RANGE_OUT = 'Archive Log!A2:I'
        LOG_IN = self.sheet.get(SPREADSHEET_ID, LOG_RANGE_IN, RENDER_OPTION)
        LOG_OUT = LOG_IN.get('values', {})
        self.sheet.add(SPREADSHEET_ID, LOG_RANGE_OUT, LOG_OUT, "ROWS")
        self.sheet.clear(SPREADSHEET_ID, LOG_RANGE_IN)

        await ctx.message.delete()
        await ctx.channel.send("`WEEKLY RESET HAS OCCURRED.`")

    @commands.command(brief='- Records an activity in the BPdia log',
                      help=LOG_HELP)
    @commands.check(is_tracker)
    async def log(self, ctx):

        start = timer()
        command_data = []
        display_errors = []
        self.user_map = self.build_user_map()
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
                return
            elif len(log_args) > num_args + offset:
                display_errors.append(EXTRA_FIELD_ERROR)
                return

            for i in range(num_args):
                arg = log_args[offset + i]
                if types[i] == 'int':
                    try:
                        arg = str(int(arg, 10))
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
                        display_errors.append(EXTRA_FIELD_ERROR)

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

        if len(display_errors) == 0:
            while len(command_data) < 7:
                command_data.append([''])  # Pad until CL and ASL
            target_id = re.sub(r'\D+', '', log_args[0])
            command_data.append([self.get_cl(target_id)])  # Because the sheet formatting has to be a little extra
            command_data.append([self.update_asl()])
            print(f'DATA: {command_data}')  # TODO: Turn this into a proper logging statement
            self.sheet.add(SPREADSHEET_ID, 'Log!A2', command_data, "COLUMNS")
            stop = timer()
            print(f'Elapsed time: {stop - start}')
            await ctx.message.channel.send(msg + ' - log submitted by ' + ctx.author.nick)
        else:
            for error in display_errors:
                await ctx.message.channel.send(error)
        await ctx.message.delete()

    @commands.command(brief='- Creates a new character on the BPdia sheet',
                      help=CREATE_HELP)
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
        DATA = [[user_id]] + list(map(lambda x: [x], args))
        # for i in args:
        #     DATA.append([i])

        reset_xp = [['0']]
        initial_log_data = [['Blind Prophet'], [str(ctx.message.created_at)], [user_id], ['BONUS'], ['Initial'],
                            [0], [0], [1], [self.update_asl()]]
        self.sheet.set(SPREADSHEET_ID, RANGE_NAME, DATA, "COLUMNS")
        self.sheet.set(SPREADSHEET_ID, XP_RANGE, reset_xp, "COLUMNS")
        self.sheet.add(SPREADSHEET_ID, 'Log!A2', initial_log_data, "COLUMNS")
        print(f'{DATA}')
        await ctx.message.delete()
        await ctx.message.channel.send(ctx.message.content[8:] + ' - create submitted by ' + ctx.author.nick)

    # --------------------------- #
    # Helper functions
    # --------------------------- #
    def update_asl(self):
        ASL_RANGE = 'Characters!B1'
        server_level = self.sheet.get(SPREADSHEET_ID, ASL_RANGE, "UNFORMATTED_VALUE")
        server_level = int(server_level['values'][0][0])
        return server_level

    def build_user_map(self):
        XPLIST_RANGE = 'Characters!I3:I'
        USERLIST_RANGE = 'Characters!A3:A'
        xp_list = self.sheet.get(SPREADSHEET_ID, XPLIST_RANGE, "FORMATTED_VALUE")
        user_list = self.sheet.get(SPREADSHEET_ID, USERLIST_RANGE, "UNFORMATTED_VALUE")
        user_list = user_list['values']
        xp_list = xp_list['values']

        return {  # Using fancy dictionary comprehension to make the dict
            str(key[0]): value[0] for key, value in zip(user_list, xp_list)
        }

    def get_cl(self, charid):
        character_level = self.user_map[charid]
        # print(f'ID: {charid}, Level (XP): {character_level}')
        return 1 + int((int(character_level) / 1000))
