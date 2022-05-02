import re
import time
from typing import List

import discord
import discord.errors
import discord.utils
from discord.ext import commands
from discord.ext.commands.context import Context
from discord.types.embed import EmbedField
from texttable import Texttable

from ProphetBot.bot import BpBot
from ProphetBot.helpers import *
from ProphetBot.models.sheets_objects import Character, BuyEntry, SellEntry, GlobalEntry

import aiopg.sa
import discord
from discord import ButtonStyle, Embed, Member, Role, Color
from discord.commands import SlashCommandGroup, CommandPermission, Option, OptionChoice, permissions
from discord.commands.context import ApplicationContext
from discord.ext import commands
from discord.ext.commands import Greedy
from discord.ui import Button

from ProphetBot.bot import BpBot
from ProphetBot.models.sheets_objects import Character, ArenaEntry, BonusEntry, RpEntry, Faction, CharacterClass
from ProphetBot.models.embeds import ErrorEmbed, LogEmbed, linebreak
from ProphetBot.queries import select_active_arena_by_channel, insert_new_arena, update_arena_tier, \
    update_arena_completed_phases, close_arena_by_id
from ProphetBot.sheets_client import GsheetsClient


def setup(bot):
    bot.add_cog(BPdia(bot))


def build_table(data):
    level = int(data['Level'])
    character_data = list()
    character_data.append(['Name', data['Name']])
    character_data.append(['Class', data['Class']])
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
        character_data.append(['RP', str(num_rp) + '/' + str(needed_rp)])
        character_data.append(['Arena', str(num_arena) + '/' + str(needed_arena)])

    table = Texttable()
    table.set_cols_align(["l", "r"])
    table.set_cols_valign(["m", "m"])
    table.add_rows(character_data)
    return table.draw()


def build_get_embed(character: Character, player: Member) -> Embed:
    """
    Puts together a character information embed for the provided player's character

    :param character: Character we're pulling the information for
    :param player: Member of the character's player
    :return: Embed object fully formatted and ready to go
    """

    description = f"**Class:** {character.character_class}\n" \
                  f"**Faction:** {character.faction}\n" \
                  f"**Level:** {character.level}\n" \
                  f"**Experience:** {character.experience} xp\n" \
                  f"**Wealth:** {character.wealth} gp"

    # Initial setup
    faction_role = discord.utils.get(player.roles, name=character.faction)
    embed = Embed(
        title=f"Character Info - {character.name}",
        description=description,
        color=faction_role.color if faction_role else Color.dark_grey()
    )
    embed.set_thumbnail(url=player.display_avatar.url)

    # First add the weekly limits
    embed.add_field(name="Weekly Limits:",
                    value=f"\u200b \u200b \u200b Diversion GP: {character.div_gp}/{character.max_gp}\n"
                          f"\u200b \u200b \u200b Diversion XP: {character.div_xp}/{character.max_xp}",
                    inline=False)
    # embed.add_field(name="Class", value=character.character_class, inline=True)
    # embed.add_field(name="Level", value=character.level, inline=True)
    # embed.add_field(name="Faction", value=character.faction, inline=True)
    # embed.add_field(**linebreak())
    # embed.add_field(name="Experience", value=f"{character.experience} xp", inline=True)
    # embed.add_field(name="Wealth", value=f"{character.wealth} gp", inline=True)
    # embed.add_field(**linebreak())
    # embed.add_field(name="Diversion GP", value=f"{character.div_gp}/{character.max_gp}", inline=True)
    # embed.add_field(name="Diversion XP", value=f"{character.div_xp}/{character.max_xp}", inline=True)
    # embed.add_field(**linebreak())

    # Then we add some new player quest info for level 1 & 2s
    if character.level < 3:
        embed.add_field(name="First Steps Quests:",
                        value=f"\u200b \u200b \u200b Level {character.level} RPs: "
                              f"{character.completed_rps}/{character.needed_rps}\n"
                              f"\u200b \u200b \u200b Level {character.level} Arenas: "
                              f"{character.completed_arenas}/{character.needed_arenas}")
        # embed.add_field(name=f"Level {character.level} RPs",
        #                 value=f"{character.completed_rps}/{character.needed_rps}", inline=True)
        # embed.add_field(name=f"Level {character.level} Arenas",
        #                 value=f"{character.completed_arenas}/{character.needed_arenas}", inline=True)

    return embed


def get_cl(char_xp):
    return 1 + int((int(char_xp) / 1000))


def get_faction_role(player: Member) -> Role:
    """
    Returns the first matching faction role of the provided player, or None if no faction roles are found

    :param player: A Member object representing the player in question
    :return: The first matching faction Role
    """
    faction_names = Faction.values_list()
    return discord.utils.find(lambda r: r.name in faction_names, player.roles)


class BPdia(commands.Cog):
    bot: BpBot  # Typing annotation for my IDE's sake

    def __init__(self, bot):
        # All GSheet endpoints are in the bot object now
        self.bot = bot
        print(f'Cog \'BPdia\' loaded')

    @commands.slash_command(
        name="create",
        description="Creates a new character",
        default_permission=False
    )
    @permissions.has_any_role("Magewright", "Council")
    async def create_character(
            self, ctx: ApplicationContext,
            player: Option(Member, "Character's player", required=True),
            name: Option(str, "Character's name", required=True),
            character_class: Option(str, "Character's (initial) class", choices=CharacterClass.option_list(),
                                    required=True),
            gp: Option(int, "Unspent starting gold", required=True),
            level: Option(int, "Starting level for higher-level characters", min_value=1, max_value=20, default=1)
    ):
        start = time.time()
        print(f'Incoming \'Create\' command invoked by {ctx.author.name}. '
              f'Args: [ {player}, {name}, {character_class}, {gp}, {level} ]')

        # Everything is built off the assumption that each player only has one active character, so check for that
        if self.bot.sheets.get_character_from_id(player.id) is not None:
            print(f"Found existing character for {player.id}, aborting")
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"Player {player.mention} already has a character. Have a Council member "
                                             f"archive the old character before creating a new one."),
                ephemeral=True
            )
            return

        xp = (level - 1) * 1000  # Base XP for level 1 is 0 XP, 2 is 1000 XP, etc
        new_character = Character(player.id, name, CharacterClass(character_class), Faction.INITIATE, gp, xp)
        initial_log = BonusEntry(f"{ctx.author.name}#{ctx.author.discriminator}", new_character, "Initial Log", 0, 0)

        self.bot.sheets.create_character(new_character)
        self.bot.sheets.log_activity(initial_log)

        embed = Embed(title=f"Character Created - {name}",
                      description=f"**Player:** {player.mention}\n"
                                  f"**Class:** {character_class}\n"
                                  f"**Starting Gold:** {gp}\n"
                                  f"**Starting Level:** {level}",
                      color=discord.Color.random())
        embed.set_thumbnail(url=player.display_avatar.url)
        embed.set_footer(text=f"Created by: {ctx.author.name}#{ctx.author.discriminator}",
                         icon_url=ctx.author.display_avatar.url)

        await ctx.response.send_message(embed=embed)
        end = time.time()
        print(f"Time to create character: {end - start}s")

    @commands.slash_command(
        name="get",
        description="Displays character information for a player's character"
    )
    async def get_character(self, ctx: ApplicationContext,
                            player: Option(Member, "Player to get the information of", required=False)):
        if player is None:
            player = ctx.author
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return

        await ctx.response.send_message(embed=build_get_embed(character, player), ephemeral=False)

    @commands.slash_command(
        name="rp",
        description="Logs a completed RP",
        default_permission=False
    )
    @permissions.has_any_role("Magewright", "Council")
    async def log_rp(self, ctx: ApplicationContext,
                     player: Option(Member, description="Player who participated in the RP", required=True)):
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return

        log_entry = RpEntry(f"{ctx.author.name}#{ctx.author.discriminator}", character)
        self.bot.sheets.log_activity(log_entry)

        await ctx.response.send_message(embed=LogEmbed(ctx, log_entry), ephemeral=False)

    @commands.slash_command(
        name="bonus",
        description="Gives bonus GP and/or XP to a player",
        default_permission=False
    )
    @permissions.has_any_role("Magewright", "Council")
    async def log_bonus(self, ctx: ApplicationContext,
                        player: Option(Member, description="Player receiving the bonus", required=True),
                        reason: Option(str, description="The reason for the bonus", required=True),
                        gold: Option(int, description="The amount of gp", default=0),
                        experience: Option(int, description="The amount of xp", default=0)):
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return

        log_entry = BonusEntry(f"{ctx.author.name}#{ctx.author.discriminator}", character, reason, gold, experience)
        self.bot.sheets.log_activity(log_entry)

        await ctx.response.send_message(embed=LogEmbed(ctx, log_entry), ephemeral=False)

    @commands.slash_command(
        name="buy",
        description="Logs the sale of an item to a player",
        default_permission=False
    )
    @permissions.has_any_role("Magewright", "Council")
    async def log_buy(self, ctx: ApplicationContext,
                      player: Option(Member, description="Player who bought the item", required=True),
                      item: Option(str, description="The item being bought", required=True),
                      cost: Option(int, description="The cost of the item", required=True)):
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return

        log_entry = BuyEntry(f"{ctx.author.name}#{ctx.author.discriminator}", character, item, cost)
        self.bot.sheets.log_activity(log_entry)

        await ctx.response.send_message(embed=LogEmbed(ctx, log_entry), ephemeral=False)

    @commands.slash_command(
        name="sell",
        description="Logs the sale of an item from a player. Not for player establishment sales",
        default_permission=False,
    )
    @permissions.has_any_role("Magewright", "Council")
    async def log_sell(self, ctx: ApplicationContext,
                       player: Option(Member, description="Player who sold the item", required=True),
                       item: Option(str, description="The item being sold", required=True),
                       cost: Option(int, description="The amount of gp received for the sale", required=True)):
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return

        log_entry = SellEntry(f"{ctx.author.name}#{ctx.author.discriminator}", character, item, cost)
        self.bot.sheets.log_activity(log_entry)

        await ctx.response.send_message(embed=LogEmbed(ctx, log_entry), ephemeral=False)

    @commands.slash_command(
        name="global",
        description="Logs a player's participation in a global",
        default_permission=False
    )
    @permissions.has_any_role("Magewright", "Council")
    async def log_global(self, ctx: ApplicationContext,
                         player: Option(Member, description="Player receiving the bonus", required=True),
                         global_name: Option(str, description="The name of the global activity", required=True),
                         gold: Option(int, description="The amount of gp", required=True),
                         experience: Option(int, description="The amount of xp", required=True)):
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return

        log_entry = GlobalEntry(f"{ctx.author.name}#{ctx.author.discriminator}", character,
                                global_name, gold, experience)
        self.bot.sheets.log_activity(log_entry)

        await ctx.response.send_message(embed=LogEmbed(ctx, log_entry), ephemeral=False)

    @commands.command(brief='- Provides a link to the public BPdia sheet')
    async def sheet(self, ctx):
        link = '<https://docs.google.com/spreadsheets/d/' + '1Ps6SWbnlshtJ33Yf30_1e0RkwXpaPy0YVFYaiETnbns' + '/>'
        await ctx.message.channel.send(f'The BPdia public sheet can be found at:\n{link}')
        await ctx.message.delete()

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
        xp_range = 'H' + str(index + 3)  # Could find the index in this same line, but that's messy
        try:
            self.bot.sheets.char_sheet.update(xp_range, new_xp)
        except Exception as E:
            await ctx.message.channel.send(f'Error occurred while sending data to the sheet')
            print(f'level exception: {type(E)}')
            return
        await ctx.message.channel.send(f'{disc_user} - level submitted by {ctx.author.nick}')
        await ctx.message.delete()

    @commands.command(brief='- Processes the weekly reset',
                      help=WEEKLY_HELP)
    @commands.has_role('Council')
    async def weekly(self, ctx):
        # Command to process the weekly reset
        await ctx.channel.send("`PROCESSING WEEKLY RESET`")
        await ctx.trigger_typing()

        # Process pending GP/XP
        pending_gp_xp = self.bot.sheets.char_sheet.batch_get(['F3:F', 'I3:I'])
        gp_total = list(pending_gp_xp[0])
        xp_total = list(pending_gp_xp[1])
        print(f'gp: {gp_total}\n'
              f'xp: {xp_total}')

        try:
            self.bot.sheets.char_sheet.batch_update([{
                'range': 'E3:E',
                'values': gp_total
            }, {
                'range': 'H3:H',
                'values': xp_total
            }])
        except gspread.exceptions.APIError as e:
            print(e)
            await ctx.channel.send("Error: Trouble getting GP/XP values. Aborting.")
            return

        # Archive old log entries
        pending_logs = self.bot.sheets.log_sheet.get('A2:I')

        try:
            self.bot.sheets.log_archive.append_rows(pending_logs, value_input_option='USER_ENTERED',
                                                    insert_data_option='INSERT_ROWS', table_range='A2')
            self.bot.sheets.bpdia_workbook.values_clear('Log!A2:I')
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
                             '', '', get_cl(user_map[str(member_id)]), int(self.bot.sheets.get_asl())])
        for member_id in magewright_ids:
            log_data.append(['Blind Prophet', str(datetime.utcnow()), str(member_id), 'MOD', '',
                             '', '', get_cl(user_map[str(member_id)]), int(self.bot.sheets.get_asl())])

        self.bot.sheets.log_sheet.append_rows(log_data, value_input_option='USER_ENTERED',
                                              insert_data_option='INSERT_ROWS',
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
            command_data.append(self.bot.sheets.get_asl())
            print(f'DATA: {command_data}')
            # flat_data = flatten(command_data)
            try:
                self.bot.sheets.log_sheet.append_row(command_data, value_input_option='USER_ENTERED',
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

    # --------------------------- #
    # Helper functions
    # --------------------------- #

    # def get_asl(self):
    #     try:
    #         server_level = self.bot.sheets.char_sheet.get('B1')
    #     except gspread.exceptions.APIError as E:
    #         print(E)
    #     return int(server_level[0][0])

    # async def _character_from_row(self, row):
    #     header_row = '2:2'
    #     user_row = f'{row}:{row}'
    #     data = self.bot.sheets.char_sheet.batch_get([header_row, user_row])
    #
    #     return await Character.create(data)

    def get_user_map(self):
        USERLIST_RANGE = 'A3:A'
        XPLIST_RANGE = 'I3:I'
        try:
            results = self.bot.sheets.char_sheet.batch_get([USERLIST_RANGE, XPLIST_RANGE])
        except gspread.exceptions.APIError as E:
            print(E)

        return {  # Using fancy dictionary comprehension to make the dict
            str(key[0]): int(value[0]) for key, value in zip(results[0], results[1])
        }

    def get_character_from_id(self, discord_id: str) -> Character:
        header_row = '2:2'
        target_cell = self.bot.sheets.char_sheet.find(discord_id, in_column=1)
        user_row = str(target_cell.row) + ':' + str(target_cell.row)

        data = self.bot.sheets.char_sheet.batch_get([header_row, user_row])
        return Character(data)
