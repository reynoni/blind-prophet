import os
import json
import discord
import math

from discord.ext.commands import Greedy
from datetime import datetime
from discord.ext import commands

from ProphetBot.helpers import *


def setup(bot):
    bot.add_cog(Arenas(bot))


def format_lod(list_of_dicts):
    formatted = []
    for item in list_of_dicts:
        formatted.append([str(item['Role ID']), str(item['Channel ID']),
                          str(item['Host']), item['Phases'], item['Tier']])
    return formatted


def get_tier(user_map, arena_role: discord.Role, host_id: int):
    # Get a list of levels for each character in the arena
    members = [get_cl(user_map[str(member.id)]) for member in arena_role.members if not(member.id == host_id)]
    # Tier is ceil(avg/4)
    avg_level = sum(members) / len(members)
    return int(math.ceil(avg_level/4))


class Arenas(commands.Cog):
    # todo: Turn all the multi-line messages into Embeds
    def __init__(self, bot):
        # Setting up some objects
        self.bot = bot
        try:
            self.drive = gspread.service_account_from_dict(json.loads(os.environ['GOOGLE_SA_JSON']))
            self.bpdia_sheet = self.drive.open_by_key(os.environ['SPREADSHEET_ID'])
            self.char_sheet = self.bpdia_sheet.worksheet('Characters')
            self.log_sheet = self.bpdia_sheet.worksheet('Log')
            self.arenas_sheet = self.bpdia_sheet.worksheet('Arenas')
        except Exception as E:
            print(E)
            print(f'Exception: {type(E)} when trying to use service account')

        print(f'Cog \'Arenas\' loaded')

    @commands.group(
        name='arena_new'
    )
    @commands.has_role('Host')
    async def arena(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(f'Missing or unrecognized subcommand for `{ctx.prefix}arena_new`. '
                           f'Use `{ctx.prefix}help arena` for more information')

    @arena.command(
        name='claim',
        aliases=['start'],
        brief='Starts an arena in the current channel',
        help=f'**@Host only**\n\n'
             f'Used to start an arena match in the current channel. '
             f'This command will fail if the channel already has an arena in progress.\n\n'
             f'Example usage: `>arena_new claim`, or `>arena_new start`'
    )
    @commands.has_role('Host')
    async def claim(self, ctx):
        list_of_dicts = self.arenas_sheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
        if ctx.channel.id in [entry.get('Channel ID', None) for entry in list_of_dicts]:
            await ctx.send(f'Error: {ctx.channel.mention} is already in use.\n'
                           f'Use `{ctx.prefix}arena_new status to check the current status of this room.')
            return
        else:
            user_map = get_user_map(self.char_sheet)

            # Creating a temporary Sheets record of this arena instance
            if not (channel_role := discord.utils.get(ctx.guild.roles, name=ctx.channel.name)):
                await ctx.send(f'Error: Role @{ctx.channel.name} doesn\'t exist. '
                               f'A Council member may need to create it.')
            else:
                self.arenas_sheet.append_row([str(channel_role.id), str(ctx.channel.id),
                                              str(ctx.author.id), 0, 1],
                                             value_input_option='RAW',
                                             insert_data_option='INSERT_ROWS',
                                             table_range='A1')
                await ctx.author.add_roles(channel_role, reason=f'{ctx.author.name} claiming {ctx.channel.name}')
                await ctx.message.delete()
                await ctx.send(f'Arena {ctx.channel.mention} successfully claimed by {ctx.author.mention}\n'
                               f'Use `{ctx.prefix}arena_new add @player1 @player2 etc` to add players to the arena.\n'
                               f'Alternatively, players can join with `{ctx.prefix}arena_new join`.')

    @claim.error
    async def claim_error(self, ctx, error):
        # todo: Better error handling. Might be prudent to make a few error classes of our own.
        await ctx.send(error)

    @arena.command(
        name='join',
        brief='Joins an active arena',
        help='Used to join the current arena. '
             'Make sure to use this command in the channel of the arena you wish to join.\n\n'
             'Example usage: `>arena_new join`'
    )
    async def join(self, ctx):
        # First we need to determine which arena this is, and whether it is in use.
        list_of_dicts = self.arenas_sheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
        arena = self.get_arena(ctx.channel.id)

        if not arena:
            await ctx.send(f'Error: {ctx.channel.mention} is already in use.\n'
                           f'Use `{ctx.prefix}arena_new status` to check the current status of this room.')
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
                    await ctx.send(f'{ctx.author.mention} successfully added to {ctx.channel.mention}')
                    self.update_tier(get_user_map(self.char_sheet), arena_role, arena['Host'], list_of_dicts)

            await ctx.message.delete()

    @arena.command(
        name='add',
        brief='Adds player(s) to an active arena',
        help='**@Host only**\n\n'
             'Used to add players to the current arena. '
             'Any number of players can be specified, each separated by a space. '
             'The host does not need to be added in this way\n\n'
             'Example usage: `>arena_new add @player1 @player2 @player3`'
    )
    @commands.has_role('Host')
    async def add(self, ctx, members: Greedy[discord.Member]):
        # First we need to determine which arena this is, and whether it is in use.
        list_of_dicts = self.arenas_sheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
        arena = self.get_arena(ctx.channel.id)

        # Lots of error checking. Should really make some custom exceptions to raise.
        if len(members) == 0:
            await ctx.send(f'Error: One or more players must be specified. '
                           f'Use `{ctx.prefix}help arena add` for more information.')
            return
        elif not arena:
            await ctx.send(f'Error: {ctx.channel.mention} is already in use.\n'
                           f'Use `{ctx.prefix}arena_new status to check the current status of this room.')
            return
        elif not ctx.author.id == arena['Host']:
            await ctx.send(f'Error: {ctx.author.mention} is not the current host of this arena.')
            return
        else:
            if not(arena_role := discord.utils.get(ctx.guild.roles, id=arena['Role ID'])):
                await ctx.send(f'Error: Role for {ctx.channel.mention} not found. Maybe Discord is having issues?')
                return
            else:
                for member in members:
                    if arena_role in member.roles:
                        await ctx.send(f'{member.mention} is already a part of {ctx.channel.mention}, skipping')
                    else:
                        await member.add_roles(arena_role, reason=f'{member.name} added to {arena_role} by '
                                                                  f'{ctx.author.name}')
                        await ctx.send(f'{member.mention} successfully added to {ctx.channel.mention}')

            self.update_tier(get_user_map(self.char_sheet), arena_role, arena['Host'], list_of_dicts)
            await ctx.message.delete()

    @arena.command(
        name='remove',
        brief='Removes player(s) from an active arena',
        help='**@Host only**\n\n'
             'Used to remove players from an arena. Any number of players can be specified, each separated by a space. '
             'To be used in cases where players are inactive or need to leave an arena for whatever reason.\n'
             '**Note:** Do **not** remove players in this way at the end of an arena.\n\n'
             'Example usage: `>arena_new remove @player1 @player2`'
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
                           f'Use `{ctx.prefix}arena_new status to check the current status of this room.')
            return
        elif not ctx.author.id == arena['Host']:
            await ctx.send(f'Error: {ctx.author.mention} is not the current host of this arena.')
            return
        else:
            if not(arena_role := discord.utils.get(ctx.guild.roles, id=arena['Role ID'])):
                await ctx.send(f'Error: Role for {ctx.channel.mention} not found. Maybe Discord is having issues?')
                return
            else:
                for member in members:
                    if arena_role in member.roles:
                        await ctx.send(f'{member.mention} is already a part of {ctx.channel.mention}, skipping')
                    else:
                        await member.remove_roles(arena_role, reason=f'{member.name} removed from {arena_role} by '
                                                                     f'{ctx.author.name}')
                        await ctx.send(f'{member.mention} successfully removed from {ctx.channel.mention}')

            await ctx.message.delete()

    @arena.command(
        name='phase',
        brief='Ends an arena phase',
        help='**@Host only**\n\n'
             'Used to log the completion of an arena phase. Accepted `result` values are \'WIN\' or \'LOSS\' '
             '(case-insensitive). '
             'This command does **not** close out an arena or give phase bonuses.\n\n'
             'Example usage: `>arena_new phase Win`'
    )
    @commands.has_role('Host')
    async def phase(self, ctx, result: str):
        # First we need to determine which arena this is, and whether it is in use.
        # In this case we need the list_of_dicts later, so we aren't using self.get_arena()
        list_of_dicts = self.arenas_sheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
        arena = None
        for item in list_of_dicts:
            if item.get('Channel ID', None) == ctx.channel.id:
                arena = item

        # Error checking
        if not arena:
            await ctx.send(f'Error: {ctx.channel.mention} is already in use.\n'
                           f'Use `{ctx.prefix}arena_new status to check the current status of this room.')
            return
        elif not (ctx.author.id == arena['Host'] or
                  discord.utils.get(ctx.guild.roles, name='Council') in ctx.author.roles):
            await ctx.send(f'Error: {ctx.author.mention} is not the current host of this arena.')
            return
        elif result.upper() not in ['WIN', 'LOSS']:
            await ctx.send(f'Error: result must be \'win\' or \'loss\'')
            return
        else:
            user_map = get_user_map(self.char_sheet)
            asl = int(get_asl(self.char_sheet))
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
            self.log_sheet.append_rows(log_data, value_input_option='RAW',
                                       insert_data_option='INSERT_ROWS', table_range='A1')

            # Update the Arenas record (number of phases only goes up on a win)
            for arena in list_of_dicts:
                if (arena['Channel ID'] == ctx.channel.id) and (result.upper() != 'LOSS'):
                    arena['Phases'] += 1

            self.arenas_sheet.update('A2:E', format_lod(list_of_dicts))

            await ctx.send(f'**Phase {arena["Phases"]} complete!**\n\n'
                           f'HOST award applied to:\n'
                           f'  {ctx.author.mention}\n'
                           f'{result.upper()} applied to:\n'
                           f'{members_string}\n'
                           f'If this was the final phase of the arena, be sure to use `{ctx.prefix}arena_new close` to '
                           f'grant phase bonuses and mark the arena as complete!')
            await ctx.message.delete()

    @arena.command(
        name='close',
        brief='Closes out an active arena',
        help='**@Host only**\n\n'
             'Used to close out a completed arena. This command awards phase bonuses if applicable.\n\n'
             'Example usage: `>arena_new close`'
    )
    @commands.has_role('Host')
    async def close(self, ctx):
        # First we need to determine which arena this is, and whether it is in use.
        list_of_dicts = self.arenas_sheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
        arena = self.get_arena(ctx.channel.id, list_of_dicts=list_of_dicts)

        if not arena:
            await ctx.send(f'Error: {ctx.channel.mention} is already in use.\n'
                           f'Use `{ctx.prefix}arena_new status to check the current status of this room.')
            return
        elif not ctx.author.id == arena['Host']:
            await ctx.send(f'Error: {ctx.author.mention} is not the current host of this arena.')
            return
        else:
            user_map = get_user_map(self.char_sheet)
            asl = int(get_asl(self.char_sheet))
            arena_role = discord.utils.get(ctx.guild.roles, id=arena['Role ID'])

            # Create the common part of the close message
            close_message = f'{ctx.channel.mention} complete!\n\n' \
                            f'**Tier:** {arena["Tier"]}\n' \
                            f'**Phases Completed:** {arena["Phases"]}\n\n' \

            # Get the tier and apply rewards if appropriate
            if (arena['Phases'] >= arena['Tier']/4) and (arena['Tier'] > 1):
                log_data = []
                for member in arena_role.members:
                    if not member.id == arena['Host']:
                        log_data.append(['Blind Prophet', str(datetime.utcnow()), str(member.id), 'ARENA',
                                         'P'+str(arena['Phases']), '', '', get_cl(user_map[str(member.id)]), asl])

                self.log_sheet.append_rows(log_data, value_input_option='RAW',
                                           insert_data_option='INSERT_ROWS', table_range='A1')

                close_message += f'Phase bonus applied to:\n'  # todo: fill this out
                for member in arena_role.members:
                    close_message += f' {member.id}\n'
                close_message += '\n'

            # Time to clean up the role and sheet
            for member in arena_role.members:
                await member.remove_roles(arena_role, reason=f'Closing {ctx.channel.name}')

            # Recreate the LoD without the current arena & update the sheet
            list_of_dicts = [item for item in list_of_dicts if (item['Channel ID'] != ctx.channel.id)]
            self.arenas_sheet.delete_row(len(list_of_dicts)+2)  # Update will leave us with an extra row if we don't
            self.arenas_sheet.update('A2:E', format_lod(list_of_dicts))

            close_message += f'Host! Please be sure to use `!br` once RP is finished so that others ' \
                             f'know this room is available.'

            await ctx.send(close_message)
            await ctx.message.delete()

    @arena.command(
        name='status',
        brief='Displays the status of the current arena',
        help='Used to show the progress of the current arena channel\n\n'
             'Example usage: `>arena_new status`'
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
            list_of_dicts = self.arenas_sheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
        for item in list_of_dicts:
            if item.get('Channel ID', None) == channel_id:
                return item
        return None

    def update_tier(self, user_map, arena_role: discord.Role, host_id: int, list_of_arenas):
        # Get the updated tier (avg player level / 4) and write it to the sheet
        for item in list_of_arenas:
            if item.get('Role ID', None) == arena_role.id:
                item['Tier'] = get_tier(user_map, arena_role, host_id)
        self.arenas_sheet.update('A2:E', format_lod(list_of_arenas))
