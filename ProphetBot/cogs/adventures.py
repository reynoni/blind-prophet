import logging
import re
import gspread
import os
import json
import typing
import discord
import asyncio
from timeit import default_timer as timer

from discord.ext.commands import Greedy
from discord import Guild, Role, RoleTags

from ProphetBot.constants import *
from datetime import datetime
from ProphetBot.helpers import *
from discord.ext import commands
from texttable import Texttable


def setup(bot):
    # print('loading_cog')
    bot.add_cog(Adventures(bot))


def clean_room_name(room_name: str):
    return room_name.strip().replace(' ', '-')


class Adventures(commands.Cog):

    def __init__(self, bot):
        # Setting up some objects
        self.bot = bot
        try:
            self.drive = gspread.service_account_from_dict(json.loads(os.environ['GOOGLE_SA_JSON']))
            self.bpdia_sheet = self.drive.open_by_key(os.environ['SPREADSHEET_ID'])
            self.char_sheet = self.bpdia_sheet.worksheet('Characters')
            self.log_sheet = self.bpdia_sheet.worksheet('Log')
            self.log_archive = self.bpdia_sheet.worksheet('Archive Log')
            self.adventures_sheet = self.bpdia_sheet.worksheet('Adventures')
            self.adventures_pending_rewards = self.bpdia_sheet.worksheet('Pending Rewards')
        except Exception as E:
            print(E)
            print(f'Exception: {type(E)} when trying to use service account')

        print(f'Cog \'Adventures\' loaded')

    @commands.command()
    async def getoverwrites(self, ctx):
        print(ctx.channel.overwrites)

    @commands.group(
        name='Adventure_new'
    )
    async def adventure(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(f'Missing subcommand for `{ctx.prefix}adventure`')
        # Todo: Maybe make this a way to check active adventures?

    @adventure.command(
        name='create',
        help=f'**@Dungeon Masters only**\n\n'
             f'Creates a channel category and role for the adventure, as well as two private channels.'
             f'Any number of DMs may be specified. These members will be rewarded as (co-)DMs by `adventure checkpoint`'
             f'and will have access to administrative bot commands.'
    )
    @commands.has_role('Council')
    async def create(self, ctx, adventure_name: str, role_name: str, dms: Greedy[discord.Member]):

        # Not sure if necessary, but Discord doesn't like spaces in channel names
        room_name = clean_room_name(adventure_name)

        if discord.utils.get(ctx.guild.roles, name=role_name):
            await ctx.send(f'Error: role `@{role_name}` already exists')
        else:
            adventure_role = await ctx.guild.create_role(name=role_name, mentionable=True,
                                                         reason=f'Created by {ctx.author.nick} for adventure '
                                                                f'{adventure_name}')
            print(f'Role {adventure_role} created')

            # Create overwrites for the new category. All channels will be synced to these overwrites
            overwrites = dict()
            overwrites[adventure_role] = discord.PermissionOverwrite(view_channel=True)
            print('Created role overwrites')
            # overwrites[discord.utils.get(ctx.guild.roles, name="Dungeon Master")] = discord.PermissionOverwrite(
            #     manage_channels=True,
            #     manage_messages=True,
            # )
            # print('Created DM overwrites')
            overwrites[discord.utils.get(ctx.guild.roles, name="Bots")] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
            )
            print('Created Bots overwrites')
            overwrites[ctx.guild.default_role] = discord.PermissionOverwrite(view_channel=False)
            print(f'Created {ctx.guild.default_role.id} overwrites')

            # Add DMs to the role & let them manage messages in their channels
            for dm in dms:
                await dm.add_roles(adventure_role, reason=f'Creating adventure {adventure_name}')
                overwrites[dm] = discord.PermissionOverwrite(manage_messages=True)

            # Create category for the adventure
            new_adventure_category = await ctx.guild.create_category_channel(
                name=adventure_name,
                overwrites=overwrites,
                reason=f'Creating category for {adventure_name}'
            )

            # Create default channels (1 IC, 1 OOC)
            ic_channel = await ctx.guild.create_text_channel(
                name=room_name,
                category=new_adventure_category,
                reason=f'Creating adventure {adventure_name} IC Room'
            )
            ooc_channel = await ctx.guild.create_text_channel(
                name=f'{room_name}-ooc',
                category=new_adventure_category,
                reason=f'Creating adventure {adventure_name} OOC Room'
            )

            # Join up the DMs' ids into a Sheets-friendly format & write the row
            dm_ids = ', '.join([str(dm.id) for dm in dms])
            self.adventures_sheet.append_row(
                [str(adventure_role.id), str(new_adventure_category.id), adventure_name, dm_ids],
                value_input_option='RAW', insert_data_option='INSERT_ROWS', table_range='A1'
            )

            dm_mentions = ' '.join([dm.mention for dm in dms])
            await ooc_channel.send(f'Adventure {adventure_role.mention} successfully created!\n'
                                   f'**IC Room:** {ic_channel.mention}\n'
                                   f'**OOC Room:** {ooc_channel.mention}\n\n'
                                   f'{dm_mentions} - Please ensure that your permissions are correct in these rooms! If'
                                   f' so, you can start adding players with `{ctx.prefix}adventure add @player(s)`. '
                                   f'See `{ctx.prefix}help adventure add` for more details.')
            await ctx.message.delete()

    @create.error
    async def create_error(self, ctx, error):
        if isinstance(error, discord.Forbidden):
            await ctx.send('Error: Bot isn\'t allowed to do that (for some reason)')
        elif isinstance(error, discord.HTTPException):
            await ctx.send('Error: Creating new role failed, please try again. If the problem persists, contact '
                           'the Council')
        elif isinstance(error, discord.InvalidArgument):
            await ctx.send(f'Error: Invalid Argument {error}')
        # else:
        #     print(error)
        #     await ctx.send('Something else went wrong?')

    @adventure.command(
        name='add'
    )
    @commands.has_role("Dungeon Master")
    async def add(self, ctx, adventure_role: discord.Role, members: Greedy[discord.Member]):
        # Adds member(s) to a given role
        if self.is_dm(adventure_role, ctx.author):
            for member in members:
                await member.add_roles(adventure_role, reason=f'{member.name} added to role {adventure_role.name} '
                                                              f'by {ctx.author.name}')
                await ctx.send(f'{member.mention} added to adventure `{adventure_role.name}`')
        else:
            await ctx.send(f'Error: You are not a DM of `{adventure_role.name}`')

    @adventure.command(
        name='remove'
    )
    @commands.has_role("Dungeon Master")
    async def remove(self, ctx, adventure_role: discord.Role, members: Greedy[discord.Member]):
        # todo: Add check to see if the caller is the DM of said role
        if self.is_dm(adventure_role, ctx.author):
            for member in members:
                if adventure_role in member.roles:
                    await member.remove_roles(adventure_role,
                                              reason=f'{member.name} added to role {adventure_role.name}'
                                                     f' by {ctx.author.name}')
                    await ctx.send(f'{member.mention} removed from adventure `{adventure_role.name}`')
                else:
                    await ctx.send(f'Error: {member.mention} not found in role `{adventure_role.name}`')
        else:
            await ctx.send(f'Error: You are not a DM of `{adventure_role.name}`')

    # @adventure.guild_only()
    @adventure.command(
        name='addroom'
    )
    @commands.has_role("Dungeon Master")
    async def addroom(self, ctx, adventure_role: discord.Role, room_name: str):
        list_of_dicts = self.adventures_sheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
        adventure = next(item for item in list_of_dicts if item['Adventure Role ID'] == adventure_role.id)

        if str(ctx.author.id) not in str(adventure['DMs']).split(', '):
            await ctx.send('Error: You are not a DM of this adventure')
        else:
            category = discord.utils.get(ctx.guild.categories, id=adventure['CategoryChannel ID'])
            new_room = await category.create_text_channel(room_name, reason=f'Additional adventure room created by '
                                                                            f'{ctx.author.name}')
            await ctx.send(f'Room {new_room.mention} successfully created by {ctx.author.mention}')
            await ctx.message.delete()

            # author_perms = ctx.message.channel.permissions_for(ctx.author)
            # if not author_perms.manage_messages:
            #     print('Things')
            #
            # old_channel = ctx.message.channel
            # overwrites = old_channel.overwrites
            # category = old_channel.category
            # new_channel = await category.create_text_channel(
            #     name=f'{room_name}',
            #     overwrites=overwrites,
            #     reason=f'Creating additional room for {adventure_role.name} - {ctx.author.name}',
            #     position=old_channel.position
            # )

    @addroom.error
    async def addroom_errors(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send('Error: Command cannot be used via private messages')

    @adventure.command(
        name='status'
    )
    async def adventure_status(self, ctx, adventure_role: discord.Role, members: Greedy[discord.Member] = None):
        if members:
            for member in members:
                if member not in adventure_role.members:
                    await ctx.send(f'Error: <{member.mention}> not found in <{adventure_role.mention}>')
                    return
        else:
            members = adventure_role.members

    # /-------------------------------------\
    # /--------------Helpers----------------\
    # /-------------------------------------\
    def is_dm(self, adventure_role: discord.Role, author: discord.Member):
        list_of_dicts = self.adventures_sheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
        adventure = next(item for item in list_of_dicts if item['Adventure Role ID'] == adventure_role.id)
        if str(author.id) in str(adventure['DMs']).split(', '):
            return True
        return False
