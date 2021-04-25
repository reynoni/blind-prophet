import logging
import re
import gspread
import os
import json
import discord
import discord.errors
from sqlalchemy.orm import sessionmaker
from timeit import default_timer as timer
from ProphetBot.constants import *
from datetime import datetime
from ProphetBot.helpers import *
from discord.ext import commands
from texttable import Texttable
# from sqlalchemy.ext.asyncio import create_async_engine


def setup(bot):
    bot.add_cog(BPdia(bot))


def build_table(data):
    level = int(data['Level'])
    character_data = []
    character_data.append(['Name', data['Name']])
    if str(data['Subrace']):
        character_data.append(['Race', data['Subrace'] + ' ' +data['Race']])
    else
        character_data.append(['Race', data['Race']])
    if str(data['Subclass 1']):
        character_data.append(['Class', data['Subclass 1'] + ' ' + data['Class 1']])
    else:
        character_data.append(['Class', data['Class 1']])
    
    if str(data['Class 2']):
        if str(data['Subclass 2']):
            character_data.append(['Class', data['Subclass 1'] + ' ' + data['Class 1']])
        else:
            character_data.append(['Class', data['Class 1']])
    character_data.append(['Faction', data['Faction']])
    character_data.append(['Level', data['Level']])
    character_data.append(['Wealth', data['Total GP']])
    character_data.append(['Experience', data['Total XP']])

    if level >= 3:
        character_data.append(['Div GP', data['Div GP'] + '/' + data['GP Max']])
        character_data.append(['Div XP', data['Div XP'] + '/' + data['XP Max']])
        character_data.append(['ASL Mod', data['ASL Mod']])
    else:
        needed_arena = 1 if level == 1 else 2
        needed_rp = 1 if level == 1 else 2
        num_arena = int(data['L1 Arena']) if level == 1 else (int(data['L2 Arena 1/2']) + int(data['L2 Arena 2/2']))
        num_rp = int(data['L1 RP']) if level == 1 else (int(data['L2 RP 1/2']) + int(data['L2 RP 2/2']))
        num_pit = int(data['L1 Pit']) if level == 1 else int(data['L2 Pit'])
        character_data.append(['RP', str(num_rp) + '/' + str(needed_rp)])
        character_data.append(['Arena', str(num_arena) + '/' + str(needed_arena)])
        character_data.append(['Pit', str(num_pit) + '/1'])

    table = Texttable()
    table.set_cols_align(["l", "r"])
    table.set_cols_valign(["m", "m"])
    table.add_rows(character_data)
    return table.draw()


def flatten(thicc_list):
    return [item for sublist in thicc_list for item in sublist]


def get_cl(char_xp):
    return 1 + int((int(char_xp) / 1000))


async def test_bi(self, ctx):
    ctx.test = 5


class BPdia(commands.Cog):

    def __init__(self, bot):
        # Setting up some objects
        self.bot = bot
        try:
            self.drive = gspread.service_account_from_dict(json.loads(os.environ['GOOGLE_SA_JSON']))
            self.bpdia_sheet = self.drive.open_by_key(os.environ['SPREADSHEET_ID'])
            self.char_sheet = self.bpdia_sheet.worksheet('Characters')
            self.log_sheet = self.bpdia_sheet.worksheet('Log')
            self.log_archive = self.bpdia_sheet.worksheet('Archive Log')
        except Exception as E:
            print(E)
            print(f'Exception: {type(E)} when trying to use service account')
        # self.user_map = self.build_user_map()
        # self.get_asl()

        print(f'Cog \'BPdia\' loaded')
        # print(f'User Map: {self.user_map}')

    @commands.command(brief='- Provides a link to the public BPdia sheet')
    async def sheet(self, ctx):
        link = '<https://docs.google.com/spreadsheets/d/' + '1Ps6SWbnlshtJ33Yf30_1e0RkwXpaPy0YVFYaiETnbns' + '/>'
        await ctx.message.channel.send(f'The BPdia public sheet can be found at:\n{link}')
        await ctx.message.delete()

    @commands.before_invoke(test_bi)
    @commands.command()
    async def time(self, ctx):
        print(ctx.test)
        await ctx.send(f'Current time (in UTC): {sheetstr(datetime.utcnow())}')

    @commands.command()
    @commands.check(is_admin)
    async def find(self, ctx, query):

        try:
            cell = self.char_sheet.find(str(query))
        except gspread.exceptions.CellNotFound as e:
            print("Failed to find anything")
            await ctx.message.channel.send(f'String \'{query}\' not found')
            return

        print("Found something at R%s, C%s" % (cell.row, cell.col))
        await ctx.message.channel.send(f'String \'{query}\' found at R{cell.row}, C{cell.col}')

    @commands.command(brief='- Manually levels initiates',
                      help=LEVEL_HELP)
    @commands.has_any_role('Tracker', 'Magewright')
    async def level(self, ctx, disc_user):
        # TODO: This duplicates XP by adding non-reset XP to reset XP
        user_map = self.get_user_map()
        print(f'{str(datetime.utcnow())} - Incoming \'Level\' command from {ctx.message.author.name}'
              f'. Args: {disc_user}')

        target = re.sub(r'\D+', '', disc_user)
        if target not in user_map:
            await ctx.message.channel.send(NAME_ERROR)
            return

        if (targetXP := int(user_map[target])) > 2000:
            await ctx.message.channel.send('Error: The targeted player has over 2000 XP. Please enter manually.')
            return
        elif targetXP < 2000:
            new_xp = targetXP + 1000
        else:
            new_xp = 1000

        print(new_xp)
        index = list(user_map.keys()).index(target)  # Dicts preserve order in Python 3. Fancy.
        xp_range = 'O' + str(index + 3)  # Could find the index in this same line, but that's messy
        try:
            self.char_sheet.update(xp_range, new_xp)
        except Exception as E:
            await ctx.message.channel.send(f'Error occurred while sending data to the sheet')
            print(f'level exception: {type(E)}')
            return
        await ctx.message.channel.send(f'{disc_user} - level submitted by {ctx.author.nick}')
        await ctx.message.delete()

    @commands.command(brief='- Displays character information for a user',
                      help=GET_HELP)
    async def get(self, ctx, target=None):
        if not target:
            target = str(ctx.author.id)
        else:
            target = re.sub(r'\D+', '', target)
        print(f'Incoming \'Get_Alt\' command. Args: {target}')

        try:
            target_cell = self.char_sheet.find(target, in_column=1)
        except gspread.exceptions.CellNotFound:
            await ctx.send(
                "'" + target + "' is not a valid input... >get for your own stats, >get @name for someone else.")
            return

        header_row = '2:2'
        user_row = str(target_cell.row) + ':' + str(target_cell.row)
        data = self.char_sheet.batch_get([header_row, user_row])

        header_data = list(data[0][0])
        char_data = list(data[1][0])
        char_map = dict()

        for i in range(len(header_data)):
            if header_data[i] != '':  # Parse out some empty columns
                char_map[header_data[i]] = str(char_data[i]).replace('*', '1')  # No idea why data is returned like this

        table = build_table(char_map)  # This is where the fun stuff lives, tbh
        await ctx.send("`" + table + "`")
        await ctx.message.delete()

    @commands.command(brief='- Processes the weekly reset',
                      help=WEEKLY_HELP)
    @commands.has_role('Council')
    async def weekly(self, ctx):
        # Command to process the weekly reset
        await ctx.channel.send("`PROCESSING WEEKLY RESET`")

        # Process pending GP/XP
        pending_gp_xp = self.char_sheet.batch_get(['M3:M', 'P3:P'])
        gp_total = list(pending_gp_xp[0])
        xp_total = list(pending_gp_xp[1])

        try:
            self.char_sheet.batch_update([{
                'range': 'L3:L',
                'values': gp_total
            }, {
                'range': 'O3:O',
                'values': xp_total
            }])
        except gspread.exceptions.APIError:
            await ctx.channel.send("Error: Trouble getting GP/XP values. Aborting.")
            return

        # Archive old log entries
        pending_logs = self.log_sheet.get('A2:I')

        try:
            self.log_archive.append_rows(pending_logs, value_input_option='USER_ENTERED',
                                         insert_data_option='INSERT_ROWS', table_range='A2')
            self.bpdia_sheet.values_clear('Log!A2:I')
        except gspread.exceptions.APIError:
            await ctx.channel.send("Error: Trouble archiving log entries. Aborting.")
            return

        # Process Council/Magewright bonuses
        user_map = self.get_user_map()
        server = ctx.guild

        role_council = discord.utils.get(server.roles, name='Council')
        council_ids = [member.id for member in role_council.members]
        role_magewright = discord.utils.get(server.roles, name='Magewright')
        magewright_ids = [member.id for member in role_magewright.members if member.id not in council_ids]

        log_data = []
        for member_id in council_ids:
            log_data.append(['Blind Prophet', str(datetime.utcnow()), str(member_id), 'ADMIN', '',
                             '', '', get_cl(user_map[str(member_id)]), int(self.get_asl())])
        for member_id in magewright_ids:
            log_data.append(['Blind Prophet', str(datetime.utcnow()), str(member_id), 'MOD', '',
                             '', '', get_cl(user_map[str(member_id)]), int(self.get_asl())])

        self.log_sheet.append_rows(log_data, value_input_option='USER_ENTERED', insert_data_option='INSERT_ROWS',
                                   table_range='A2')

        await ctx.message.delete()
        await ctx.channel.send("`WEEKLY RESET HAS OCCURRED.`")

    @commands.command(brief='- Records an activity in the BPdia log',
                      help=LOG_HELP)
    @commands.has_any_role('Tracker', 'Magewright', 'Loremaster')
    async def log(self, ctx, *log_args):
        # start = timer()
        command_data = []
        display_errors = []
        user_map = self.get_user_map()

        print(f'{str(datetime.utcnow())} - Incoming \'Log\' command from {ctx.message.author.name}'
              f'. Args: {log_args}')  # TODO: This should log actual time, not message time
        log_args = list(filter(lambda a: a != '.', log_args))

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

                command_data.append(arg)

        if 2 <= len(log_args):

            # Start off by logging the user submitting the message and the date/time
            command_data.append(ctx.message.author.name)
            command_data.append(str(datetime.utcnow()))

            # Get the user targeted by the log command
            target_id = re.sub(r'\D+', '', log_args[0])
            if target_id not in user_map:
                display_errors.append(NAME_ERROR)
            else:
                command_data.append(target_id)

            # Get the activity type being logged
            activity = log_args[1].upper()
            if activity not in ACTIVITY_TYPES:  # Grabbing ACTIVITY_TYPES from constants.py
                display_errors.append(ACTIVITY_ERROR)
            else:
                command_data.append(activity)

            if len(display_errors) == 0:
                # Handle RP
                if activity in ['RP', 'MOD', 'ADMIN']:
                    if len(log_args) > 2:
                        display_errors.append(EXTRA_FIELD_ERROR)

                # Handle PIT/ARENA
                elif activity in ['ARENA_OLD', 'PIT']:
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
                elif activity in ['QUEST', 'ACTIVITY', 'CAMPAIGN', 'BONUS', 'GLOBAL']:
                    parse_activity('str', 'int', 'int')

                else:
                    display_errors.append('How did you even get here?')
        else:
            display_errors.append('Error: There must be 2-5 fields entered.')

        if len(display_errors) == 0:
            while len(command_data) < 7:
                command_data.append('')  # Pad until CL and ASL
            target_id = re.sub(r'\D+', '', log_args[0])
            command_data.append(get_cl(user_map[target_id]))  # Because the sheet formatting has to be a little extra
            command_data.append(self.get_asl())
            print(f'DATA: {command_data}')
            # flat_data = flatten(command_data)
            try:
                self.log_sheet.append_row(command_data, value_input_option='USER_ENTERED',
                                          insert_data_option='INSERT_ROWS', table_range='A2')
                await ctx.message.channel.send(f'{log_args} - log submitted by {ctx.author.nick}')
            except Exception as E:
                if isinstance(E, gspread.exceptions.APIError):
                    await ctx.message.send('Error: Something went wrong while writing the log entry. Please try again.')
            # stop = timer()
            # print(f'Elapsed time: {stop - start}')
            await ctx.message.delete()
        else:
            for error in display_errors:
                await ctx.message.channel.send(error)

    @commands.command(brief='- Alias for logging an activity', aliases=ACTIVITY_TYPES,
                      help=LOG_ALIAS_HELP)
    @commands.has_any_role('Tracker', 'Magewright', 'Loremaster')
    async def log_alias(self, ctx, *args):
        msg = str(ctx.message.content).split()
        activity = msg[0][1:]

        print(f'{str(datetime.utcnow())} - Incoming \'{activity}\' command from {ctx.message.author.name}'
              f'. Args: {args}')  # TODO: This should log actual time, not message time

        args = list(filter(lambda a: a != '.', args))
        args.insert(1, activity)
        await self.log(ctx, *args)

    @commands.command(brief='- Creates a new character on the BPdia sheet',
                      help=CREATE_HELP)
    @commands.has_any_role('Tracker', 'Magewright')
    async def create(self, ctx, member: discord.Member, name: str, character_race: str, character_subrace: str, character_class: str, character_subclass: str, gp: int):

        data = [str(member.id), name, 'Initiate', character_race, character_subrace, character_class, character_subclass gp]
        print(f'Incoming \'Create\' command. Args: {data}')

        if character_class not in ['Artificer', 'Barbarian', 'Bard', 'Cleric', 'Druid', 'Fighter', 'Monk', 'Paladin',
                                   'Ranger', 'Rogue', 'Sorcerer', 'Warlock', 'Wizard']:
            ctx.send(f"Error: Class \'{character_class}\' Unrecognized. Was your capitalization correct?")
            return
        else:
            data.extend(['', '', 0])
            initial_log_data = ['Blind Prophet', str(datetime.utcnow()), str(member.id), 'BONUS', 'Initial',
                                0, 0, 1, int(self.get_asl())]

            self.char_sheet.append_row(data, value_input_option='USER_ENTERED',
                                       insert_data_option='INSERT_ROWS', table_range='A2')
            self.log_sheet.append_row(initial_log_data, insert_data_option='INSERT_ROWS',
                                      value_input_option='USER_ENTERED', table_range='A2')

            await ctx.message.channel.send(f'{data} - create submitted by {ctx.author.nick}')
            await ctx.message.delete()


    @create.error
    async def bpdia_errors(self, ctx, error):
        message = 'Error: {error}'
        if isinstance(error, commands.MemberNotFound):
            message += f' Make sure this argument is a @Mention or a Discord ID'
        elif isinstance(error, commands.MissingAnyRole) or isinstance(error, commands.MissingRole):
            message = f'Naughty, naughty {ctx.author.mention}'

        await ctx.send(message)

    # --------------------------- #
    # Helper functions
    # --------------------------- #

    def get_asl(self):
        try:
            server_level = self.char_sheet.get('B1')
        except gspread.exceptions.APIError as E:
            print(E)
        return int(server_level[0][0])

    def get_user_map(self):
        USERLIST_RANGE = 'A3:A'
        XPLIST_RANGE = 'P3:P'
        try:
            results = self.char_sheet.batch_get([USERLIST_RANGE, XPLIST_RANGE])
        except gspread.exceptions.APIError as E:
            print(E)

        return {  # Using fancy dictionary comprehension to make the dict
            str(key[0]): int(value[0]) for key, value in zip(results[0], results[1])
        }
