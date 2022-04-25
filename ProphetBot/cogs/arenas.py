import asyncio
import bisect
from typing import List

import aiopg.sa
import math

import discord
from discord import ButtonStyle, Embed, Option, Member
from discord.commands import SlashCommandGroup, CommandPermission
from discord.commands.context import ApplicationContext
from discord.ext import commands
from discord.ext.commands import Greedy
from discord.ui import Button

from gspread.spreadsheet import Spreadsheet

from time import perf_counter

from ProphetBot.bot import BpBot
from ProphetBot.models.sheets_objects import Character
from ProphetBot.queries import select_active_arena_by_channel, insert_new_arena, update_arena_tier
from ProphetBot.helpers import *
from ProphetBot.sheets_client import GsheetsClient

from statistics import mean


def setup(bot):
    bot.add_cog(Arenas(bot))


def format_player_list(players: List[Member]):
    return "\n".join([f"-{p.mention}" for p in players])


def format_lod(list_of_dicts):
    # Format a gspread list of dicts into a list of lists so that we can write it back to the worksheet.
    # No idea why we can fetch data as a LoD, but not write it using that same format
    # Only works for entries on the 'Arenas' sheet
    formatted = []
    for item in list_of_dicts:
        formatted.append([str(item['Role ID']), str(item['Channel ID']),
                          str(item['Host']), item['Phases'], item['Tier']])
    return formatted


def get_tier(user_map, arena_role: discord.Role, host_id: int) -> int:
    # Get a list of levels for each character in the arena
    members = [get_cl(user_map[str(member.id)]) for member in arena_role.members if not (member.id == host_id)]
    # Tier is ceil(avg/4)
    avg_level = sum(members) / len(members)
    return int(math.ceil(avg_level / 4))


async def _remove_from_board(ctx, member: discord.Member):
    def predicate(message):
        return message.author == member

    arena_board = discord.utils.get(ctx.guild.channels, name='arena-board')
    try:
        deleted_messages = await arena_board.purge(check=predicate)
        print(f'{len(deleted_messages)} messages by {member.display_name} deleted from #{arena_board.name}')
    except Exception as error:
        if isinstance(error, discord.errors.HTTPException):
            await ctx.send(f'Warning: deleting user\'s post(s) from {arena_board.mention} failed')
        else:
            print(error)


async def add_to_arena(interaction: discord.Interaction, db: aiopg.sa.Engine,
                       sheets_client: GsheetsClient, player: discord.Member):
    async with db.acquire() as conn:
        results = await conn.execute(select_active_arena_by_channel(interaction.channel_id))
        arena_row = await results.first()
    # Check to make sure the arena and role exist. Send an error message and abort if they don't
    if not arena_row:
        await interaction.response.send_message(f"Error: No active arena present in this channel", ephemeral=True)
        return
    if not (channel_role := discord.utils.get(interaction.guild.roles, id=arena_row.role_id)):
        await interaction.response.send_message(f"Error: Role @{interaction.channel.name} doesn\'t exist. "
                                                f"A Council member may need to create it.", ephemeral=True)
        return
    if discord.utils.get(channel_role.members, id=player.id):
        await interaction.response.send_message(f"Error: {player.mention} is already a participant in this arena.",
                                                ephemeral=True)
        return

    # Everything looks good, so we can add the user to the role and determine the tier
    await player.add_roles(channel_role, reason=f"Joining {interaction.channel.name}")

    members_in_arena = [m.id for m in channel_role.members if m.id != arena_row.host_id]
    characters = sheets_client.get_all_characters()
    characters_in_arena = [c for c in characters if c.player_id in members_in_arena]
    tier = determine_tier(characters_in_arena)

    async with db.acquire() as conn:
        await conn.execute(update_arena_tier(arena_id=arena_row.id, new_tier=tier))

    await _remove_from_board(interaction, player)
    await interaction.response.send_message(f"{player.mention} has joined the arena!")


def determine_tier(characters: List[Character]):
    average_level = mean([c.level for c in characters])
    return bisect.bisect(TIERS, average_level)


class Arenas(commands.Cog):
    # todo: Turn all the multi-line messages into Embeds
    bot: BpBot  # Typing annotation for my IDE's sake
    arena_commands = SlashCommandGroup("arena", "Commands related to arena management.")

    class JoinArenaView(discord.ui.View):
        db: aiopg.sa.Engine
        sheets_client: GsheetsClient

        def __init__(self, db: aiopg.sa.Engine, sheets_client: GsheetsClient):
            super().__init__(timeout=None)
            self.db = db
            self.sheets_client = sheets_client

        @discord.ui.button(label="Join Arena", custom_id="join_arena", style=ButtonStyle.primary)
        async def view_callback(self, button: Button, interaction: discord.Interaction):
            await add_to_arena(interaction, self.db, self.sheets_client, interaction.user)

    def __init__(self, bot):
        self.bot = bot
        print(f'Cog \'Arenas\' loaded')

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(0.5)
        self.bot.add_view(self.JoinArenaView(self.bot.db, self.bot.sheets))

    @commands.group(
        name='arena',
        aliases=['ar'],
        help='Command group used for Arena tracking. '
             'Use `>help arena [subcommand]` for detailed information on using that subcommand.'
    )
    async def arena(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(f'Missing or unrecognized subcommand for `{ctx.prefix}arena`. '
                           f'Use `{ctx.prefix}help arena` for more information')

    @arena_commands.command(
        name="test",
        description="Used for testing stuff"
    )
    async def general_test(self, ctx: ApplicationContext):
        start = perf_counter()
        self.bot.sheets.get_all_characters()
        stop = perf_counter()
        print(f"Time to get all characters: {stop - start}s")

    @arena_commands.command(
        name="status",
        description="Shows the current participants in and status of this arena"
    )
    async def arena_status(self, ctx: ApplicationContext):
        async with self.bot.db.acquire() as conn:
            results = await conn.execute(select_active_arena_by_channel(ctx.channel_id))
            arena_row = await results.first()

        embed = Embed(color=discord.Color.random(), title=f"{ctx.channel.name.title()} Status")

        if arena_row:
            host = discord.utils.get(ctx.guild.members, id=arena_row.host_id)
            channel_role = discord.utils.get(ctx.guild.channels, id=arena_row.channel_id)
            players = [p for p in channel_role.members if p.id != host.id]
            embed.description = f"**Tier:** {arena_row.tier if arena_row.tier > 0 else 'N/A'}\n" \
                                f"**Completed Phases:** {arena_row.completed_phases} / {MAX_PHASES[arena_row.tier]}"
            embed.add_field(name="Host:",
                            value=f"-{host.mention}",
                            inline=False)
            embed.add_field(name="Players:",
                            value=format_player_list(players),
                            inline=False)
        else:
            embed.description = f"{ctx.channel.mention} is not currently in use. " \
                                f"Use `/arena claim` if you would like to start an arena!"

        await ctx.response.send_message(embed=embed, ephemeral=False)

    # @discord.commands.permissions.has_role("Host")
    @arena_commands.command(
        name="claim",
        description="Opens an arena in this channel and sets you as the host.",
        permissions=[CommandPermission(795007163625766923, 1)]
    )
    async def arena_claim(self, ctx: ApplicationContext):
        async with self.bot.db.acquire() as conn:
            results = await conn.execute(select_active_arena_by_channel(ctx.channel_id))
            row = await results.first()

        # First check to see if there is already an active arena in this channel,
        # then check to see if the associated role exists
        if row:
            await ctx.respond(f'Error: {ctx.channel.mention} is already in use.\n'
                              f'Use `/arena status` to check the current status of this room.')
            return
        if not (channel_role := discord.utils.get(ctx.guild.roles, name=ctx.channel.name)):
            await ctx.respond(f'Error: Role @{ctx.channel.name} doesn\'t exist. '
                              f'A Council member may need to create it.')
            return

        # Everything looks good, so we can create the arena record
        async with self.bot.db.acquire() as conn:
            await conn.execute(insert_new_arena(ctx.channel_id, channel_role.id, ctx.user.id))

        await ctx.user.add_roles(channel_role, reason=f"Claiming {ctx.channel.name}")
        await ctx.respond(embed=Embed(title="Arena Claimed", color=discord.Color.random(),
                                      description=f"{ctx.user.mention} has begun an arena in this channel!\n\n"
                                                  f"Click the button below or use `/arena join` to join in!"),
                          view=self.JoinArenaView(db=self.bot.db, sheets_client=self.bot.sheets))

    @arena_commands.command(
        name="join",
        description="Joins the arena in this channel"
    )
    async def arena_join(self, ctx: ApplicationContext):
        await add_to_arena(ctx.interaction, self.bot.db, self.bot.sheets, ctx.user)

    @discord.commands.permissions.has_role("Host")
    @arena_commands.command(
        name="add",
        description="Adds the specified player to the arena in this channel"
    )
    async def arena_add(self, ctx: ApplicationContext,
                        player: Option(Member, "The player to add", required=True)):
        await add_to_arena(ctx.interaction, self.bot.db, self.bot.sheets, player)

    @discord.commands.permissions.has_role("Host")
    @arena_commands.command(
        name="remove",
        description="Removes the specified player from the arena"
    )
    async def arena_remove(self, ctx: ApplicationContext,
                           player: Option(Member, "The player to remove", required=True)):
        async with self.bot.db.acquire() as conn:
            results = await conn.execute(select_active_arena_by_channel(ctx.channel_id))
            arena_row = await results.first()
        if not arena_row:
            await ctx.response.send_message(f"Error: No active arena present in this channel", ephemeral=True)
            return
        channel_role = discord.utils.get(ctx.guild.roles, id=arena_row.role_id)
        if not (discord.utils.get(channel_role.members, id=player.id)):
            await ctx.response.send_message(f"Error: {player.mention} is not a participant in this arena.",
                                            ephemeral=True)
            return

        await player.remove_roles(channel_role, reason=f"Leaving {ctx.channel.name}")

        # We only want to recalculate the tier if the arena hasn't started/is in the first phase
        if arena_row.completed_phases == 0:
            members_in_arena = [m.id for m in channel_role.members if m.id != arena_row.host_id]
            characters = self.bot.sheets.get_all_characters()
            characters_in_arena = [c for c in characters if c.player_id in members_in_arena]
            new_tier = determine_tier(characters_in_arena)

            async with self.bot.db.acquire() as conn:
                await conn.execute(update_arena_tier(arena_row.id, new_tier))

        await ctx.response.send_message(f"{player.mention} has been removed from the arena")


    @arena.command(
        name='claim',
        aliases=['start', 'c'],
        brief='Starts an arena in the current channel',
        help=f'**@Host only**\n\n'
             f'Used to start an arena match in the current channel. '
             f'This command will fail if the channel already has an arena in progress.\n\n'
             f'Example usage: `>arena claim`, or `>arena start`'
    )
    @commands.has_role('Host')
    async def claim(self, ctx):
        list_of_dicts = self.bot.sheets.arenas_sheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
        if ctx.channel.id in [entry.get('Channel ID', None) for entry in list_of_dicts]:
            await ctx.send(f'Error: {ctx.channel.mention} is already in use.\n'
                           f'Use `{ctx.prefix}arena status to check the current status of this room.')
            return
        else:

            # Creating a temporary Sheets record of this arena instance
            if not (channel_role := discord.utils.get(ctx.guild.roles, name=ctx.channel.name)):
                await ctx.send(f'Error: Role @{ctx.channel.name} doesn\'t exist. '
                               f'A Council member may need to create it.')
            else:
                self.bot.sheets.arenas_sheet.append_row([str(channel_role.id), str(ctx.channel.id),
                                                         str(ctx.author.id), 0, 1],
                                                        value_input_option='RAW',
                                                        insert_data_option='INSERT_ROWS',
                                                        table_range='A1')
                await ctx.author.add_roles(channel_role, reason=f'{ctx.author.name} claiming {ctx.channel.name}')
                await ctx.message.delete()
                await ctx.send(f'Arena {ctx.channel.mention} successfully claimed by {ctx.author.mention}\n'
                               f'Use `{ctx.prefix}arena add @player1 @player2 etc` to add players to the arena.\n'
                               f'Alternatively, players can join with `{ctx.prefix}arena join`.')

    @claim.error
    async def claim_error(self, ctx, error):
        # todo: Better error handling. Might be prudent to make a few error classes of our own.
        await ctx.send(error)

    @arena.command(
        name='join',
        aliases=['j'],
        brief='Joins an active arena',
        help='Used to join the current arena. '
             'Make sure to use this command in the channel of the arena you wish to join.\n\n'
             'Example usage: `>arena join`'
    )
    async def join(self, ctx):
        # First we need to determine which arena this is, and whether it is in use.
        list_of_dicts = self.bot.sheets.arenas_sheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
        arena = self.get_arena(ctx.channel.id)

        if not arena:
            await ctx.send(f'Error: {ctx.channel.mention} is already in use.\n'
                           f'Use `{ctx.prefix}arena status` to check the current status of this room.')
            return
        else:
            if not (arena_role := discord.utils.get(ctx.guild.roles, id=arena['Role ID'])):
                await ctx.send(f'Error: Role for {ctx.channel.mention} not found. Maybe Discord is having issues?')
                return
            else:
                if arena_role in ctx.author.roles:
                    await ctx.send(f'Error: You are already part of {ctx.channel.mention}')
                else:
                    await ctx.author.add_roles(arena_role, reason=f'{ctx.author.name} is adding themself to '
                                                                  f'{arena_role.name}')
                    await _remove_from_board(ctx, ctx.author)
                    await ctx.send(f'{ctx.author.mention} successfully added to {ctx.channel.mention}')
                    self.update_tier(get_user_map(self.bot.sheets.char_sheet), arena_role, arena['Host'], list_of_dicts)

            await ctx.message.delete()

    @join.error
    async def join_error(self, ctx, error):
        print(f'Error: {error}')

    @arena.command(
        name='add',
        aliases=['a'],
        brief='Adds player(s) to an active arena',
        help='**@Host only**\n\n'
             'Used to add players to the current arena. '
             'Any number of players can be specified, each separated by a space. '
             'The host does not need to be added in this way\n\n'
             '*Args:*\n'
             '  `players`: The player(s) to be added. Formatted as any number of mentions or Discord IDs.\n'
             '\n'
             'Example usage: `>arena add @player1 @player2 @player3`'
    )
    @commands.has_role('Host')
    async def add(self, ctx, members: Greedy[discord.Member]):
        # First we need to determine which arena this is, and whether it is in use.
        list_of_dicts = self.bot.sheets.arenas_sheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
        arena = self.get_arena(ctx.channel.id)

        # Lots of error checking. Should really make some custom exceptions to raise.
        if len(members) == 0:
            await ctx.send(f'Error: One or more players must be specified. '
                           f'Use `{ctx.prefix}help arena add` for more information.')
            return
        elif not arena:
            await ctx.send(f'Error: {ctx.channel.mention} is already in use.\n'
                           f'Use `{ctx.prefix}arena status to check the current status of this room.')
            return
        elif not ctx.author.id == arena['Host']:
            await ctx.send(f'Error: {ctx.author.mention} is not the current host of this arena.')
            return
        else:
            if not (arena_role := discord.utils.get(ctx.guild.roles, id=arena['Role ID'])):
                await ctx.send(f'Error: Role for {ctx.channel.mention} not found. Maybe Discord is having issues?')
                return
            else:
                for member in members:
                    if arena_role in member.roles:
                        await ctx.send(f'{member.mention} is already a part of {ctx.channel.mention}, skipping')
                    else:
                        await member.add_roles(arena_role, reason=f'{member.name} added to {arena_role} by '
                                                                  f'{ctx.author.name}')
                        await _remove_from_board(ctx, member)
                        await ctx.send(f'{member.mention} successfully added to {ctx.channel.mention}')

            self.update_tier(get_user_map(self.bot.sheets.char_sheet), arena_role, arena['Host'], list_of_dicts)
            await ctx.message.delete()

    @arena.command(
        name='remove',
        aliases=['re'],
        brief='Removes player(s) from an active arena',
        help='**@Host only**\n\n'
             'Used to remove players from an arena. Any number of players can be specified, each separated by a space. '
             'To be used in cases where players are inactive or need to leave an arena for whatever reason.\n'
             '**Note:** Do **not** remove players in this way at the end of an arena.\n\n'
             '*Args:*\n'
             '  `players`: The player(s) to be removed. Formatted as any number of mentions or Discord IDs.\n'
             '\n'
             'Example usage: `>arena remove @player1 @player2`'
    )
    @commands.has_role('Host')
    async def remove(self, ctx, members: Greedy[discord.Member]):
        # First we need to determine which arena this is, and whether it is in use.
        arena = self.get_arena(ctx.channel.id)

        if len(members) == 0:
            await ctx.send(f'Error: One or more players must be specified. '
                           f'Use `{ctx.prefix}help arena add` for more information.')
            return
        elif not arena:
            await ctx.send(f'Error: {ctx.channel.mention} is already in use.\n'
                           f'Use `{ctx.prefix}arena status to check the current status of this room.')
            return
        elif not ctx.author.id == arena['Host']:
            await ctx.send(f'Error: {ctx.author.mention} is not the current host of this arena.')
            return
        else:
            if not (arena_role := discord.utils.get(ctx.guild.roles, id=arena['Role ID'])):
                await ctx.send(f'Error: Role for {ctx.channel.mention} not found. Maybe Discord is having issues?')
                return
            else:
                for member in members:
                    if not (arena_role in member.roles):
                        await ctx.send(f'{member.mention} is not a member of {ctx.channel.mention}, skipping')
                    else:
                        await member.remove_roles(arena_role, reason=f'{member.name} removed from {arena_role} by '
                                                                     f'{ctx.author.name}')
                        await ctx.send(f'{member.mention} successfully removed from {ctx.channel.mention}')

            await ctx.message.delete()

    @arena.command(
        name='phase',
        aliases=['p'],
        brief='Ends an arena phase',
        help='**@Host only**\n\n'
             'Used to log the completion of an arena phase. '
             'This command does **not** close out an arena or give phase bonuses.\n\n'
             '*Args:*\n'
             '  `result`: The result of the arena as a case-insensitive string. '
             'Accepted values are \'WIN\' or \'LOSS\'\n'
             '\n'
             'Example usage: `>arena phase win`'
    )
    @commands.has_role('Host')
    async def phase(self, ctx, result: str):
        # First we need to determine which arena this is, and whether it is in use.
        # In this case we need the list_of_dicts later, so we aren't using self.get_arena()
        list_of_dicts = self.bot.sheets.arenas_sheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
        arena = self.get_arena(ctx.channel.id, list_of_dicts)

        # Error checking
        if not arena:
            await ctx.send(f'Error: {ctx.channel.mention} is already in use.\n'
                           f'Use `{ctx.prefix}arena status to check the current status of this room.')
            return
        elif not (ctx.author.id == arena['Host'] or
                  discord.utils.get(ctx.guild.roles, name='Council') in ctx.author.roles):
            await ctx.send(f'Error: {ctx.author.mention} is not the current host of this arena.')
            return
        elif result.upper() not in ['WIN', 'LOSS']:
            await ctx.send(f'Error: result must be \'win\' or \'loss\'')
            return
        else:
            user_map = get_user_map(self.bot.sheets.char_sheet)
            asl = int(get_asl(self.bot.sheets.char_sheet))
            arena_role = discord.utils.get(ctx.guild.roles, id=arena['Role ID'])

            # Time to build the list of lists that we will send to Sheets
            log_data = [['Blind Prophet', str(datetime.utcnow()), str(ctx.author.id), 'ARENA',
                         'HOST', '', '', get_cl(user_map[str(ctx.author.id)]), asl]]
            members_string = ''
            for member in arena_role.members:
                if not member.id == arena['Host']:
                    log_data.append(['Blind Prophet', str(datetime.utcnow()), str(member.id), 'ARENA',
                                     result.upper(), '', '', get_cl(user_map[str(member.id)]), asl])
                    members_string += f'  {member.mention}\n'

            # Actually send the data
            self.bot.sheets.log_sheet.append_rows(log_data, value_input_option='USER_ENTERED',
                                                  insert_data_option='INSERT_ROWS', table_range='A1')

            # Update the Arenas record (number of phases only goes up on a win)
            # todo: display_phases is jank and I don't like it
            if result.upper() != 'LOSS':
                arena['Phases'] += 1
                display_phases = arena['Phases']
            else:
                display_phases = arena['Phases'] + 1

            self.bot.sheets.arenas_sheet.update('A2:E', format_lod(list_of_dicts))

            await ctx.send(f'**Phase {display_phases} complete!**\n\n'
                           f'HOST award applied to:\n'
                           f'  {ctx.author.mention}\n'
                           f'{result.upper()} applied to:\n'
                           f'{members_string}\n'
                           f'If this was the final phase of the arena, be sure to use `{ctx.prefix}arena close` to '
                           f'grant phase bonuses and mark the arena as complete!')
            await ctx.message.delete()

    @arena.command(
        name='close',
        aliases=['cl'],
        brief='Closes out an active arena',
        help='**@Host only**\n\n'
             'Used to close out a completed arena. This command awards phase bonuses if applicable.\n\n'
             'Example usage: `>arena close`'
    )
    @commands.has_role('Host')
    async def close(self, ctx):
        # First we need to determine which arena this is, and whether it is in use.
        list_of_dicts = self.bot.sheets.arenas_sheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
        arena = self.get_arena(ctx.channel.id, list_of_dicts=list_of_dicts)

        if not arena:
            await ctx.send(f'Error: {ctx.channel.mention} is already in use.\n'
                           f'Use `{ctx.prefix}arena status to check the current status of this room.')
            return
        elif not ctx.author.id == arena['Host']:
            await ctx.send(f'Error: {ctx.author.mention} is not the current host of this arena.')
            return
        else:
            user_map = get_user_map(self.bot.sheets.char_sheet)
            asl = int(get_asl(self.bot.sheets.char_sheet))
            arena_role = discord.utils.get(ctx.guild.roles, id=arena['Role ID'])
            print(f'Arena to be closed: {arena}')

            # Create the common part of the close message
            close_message = f'{ctx.channel.mention} complete!\n\n' \
                            f'**Tier:** {arena["Tier"]}\n' \
                            f'**Phases Completed:** {arena["Phases"]}\n\n' \
 \
                # Get the tier and apply rewards if appropriate
            if (arena['Phases'] >= arena['Tier']) and (arena['Tier'] > 1):
                log_data = []
                close_message += f'Phase bonus applied to:\n'

                for member in arena_role.members:
                    if not member.id == arena['Host']:
                        close_message += f' {member.nick}\n'
                        log_data.append(['Blind Prophet', str(datetime.utcnow()), str(member.id), 'ARENA',
                                         'P' + str(arena['Phases']), '', '', get_cl(user_map[str(member.id)]), asl])

                self.bot.sheets.log_sheet.append_rows(log_data, value_input_option='USER_ENTERED',
                                                      insert_data_option='INSERT_ROWS', table_range='A1')
                close_message += '\n'

            # Time to clean up the role and sheet
            for member in arena_role.members:
                await member.remove_roles(arena_role, reason=f'Closing {ctx.channel.name}')

            # Recreate the LoD without the current arena & update the sheet
            list_of_dicts = [item for item in list_of_dicts if (item['Channel ID'] != ctx.channel.id)]
            self.bot.sheets.arenas_sheet.delete_row(
                len(list_of_dicts) + 2)  # Update will leave us with an extra row if we don't
            self.bot.sheets.arenas_sheet.update('A2:E', format_lod(list_of_dicts))

            close_message += f'Host! Please be sure to use `!br` once RP is finished so that others ' \
                             f'know this room is available.'

            await ctx.send(close_message)
            await ctx.message.delete()

    @arena.command(
        name='status',
        aliases=['s'],
        brief='Displays the status of the current arena',
        help='Used to show the progress of the current arena channel\n\n'
             'Example usage: `>arena status`'
    )
    async def status(self, ctx):
        arena = self.get_arena(ctx.channel.id)
        if not arena:
            await ctx.send(f'{ctx.channel.mention} is currently free')
        else:
            arena_role = discord.utils.get(ctx.guild.roles, id=arena['Role ID'])
            host = discord.utils.get(ctx.guild.members, id=arena['Host'])

            status_string = f'{ctx.channel.mention} has completed **{arena["Phases"]}** phase(s)\n' \
                            f'**Tier:** {arena["Tier"]}\n\n' \
                            f'**Host:**\n' \
                            f'  {host.nick}\n' \
                            f'**Players:**\n'

            for member in arena_role.members:
                if member != host:
                    status_string += f'  {member.nick}\n'

            await ctx.send(status_string)
        await ctx.message.delete()

    # --------------------------- #
    # Helper functions
    # --------------------------- #

    def get_arena(self, channel_id: int, list_of_dicts=None):
        # No point in getting the LoD again if the command already has it (for writing purposes)
        if not list_of_dicts:
            list_of_dicts = self.bot.sheets.arenas_sheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
        for item in list_of_dicts:
            if item.get('Channel ID', None) == channel_id:
                return item
        return None

    def update_tier(self, user_map, arena_role: discord.Role, host_id: int, list_of_arenas):
        # Get the updated tier (avg player level / 4) and write it to the sheet
        for item in list_of_arenas:
            if item.get('Role ID', None) == arena_role.id:
                item['Tier'] = get_tier(user_map, arena_role, host_id)
        self.bot.sheets.arenas_sheet.update('A2:E', format_lod(list_of_arenas))
