import os
import json
import discord

from discord.ext.commands import Greedy
from ProphetBot.helpers import *
from discord.ext import commands


def setup(bot):
    # print('loading_cog')
    bot.add_cog(Adventures(bot))


def clean_room_name(room_name: str):
    return room_name.strip().replace(' ', '-')


def get_dms(adventure_dict):
    return str(adventure_dict['DMs']).split(', ')


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
        name='adventure'
    )
    async def adventure(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(f'Missing subcommand for `{ctx.prefix}adventure`')
        # Todo: Maybe make this a way to check active adventures?

    @adventure.command(
        name='create',
        help='**@Council/Loremaster only**\n\n'
             'Creates a channel category and role for the adventure, as well as two private channels.'
             'Any number of DMs may be specified. These members will be rewarded as (co-)DMs by `a command to be '
             'added later` and will have access to administrative bot commands.\n\n'
             '*Args:*\n'
             '  `adventure_name`: The name of the adventure as it should show up in the category and channel names\n'
             '  `role_name`: The name of the Role to be created for adventure participants\n'
             '  `dms`: The DM(s) of the adventure, formatted as an @mention or as a Discord ID. '
             'Multiple DMs should each be separated by a space.\n'
             '\n'
             'Example usage: `>adventure create \"1 Beginner Adventure\" \"Beginners\" @DM1 @DM2`'
    )
    @commands.has_any_role('Council', 'Loremaster')
    async def create(self, ctx, adventure_name: str, role_name: str, dms: Greedy[discord.Member]):

        # Not sure if necessary, but Discord doesn't like spaces in channel names
        room_name = clean_room_name(adventure_name)

        if discord.utils.get(ctx.guild.roles, name=role_name):
            await ctx.send(f'Error: role `@{role_name}` already exists')
            return
        elif len(dms) == 0:
            await ctx.send(f'Error: one or more DMs must be specified, either by @user mention or Discord ID')
            return
        else:
            adventure_role = await ctx.guild.create_role(name=role_name, mentionable=True,
                                                         reason=f'Created by {ctx.author.nick} for adventure '
                                                                f'{adventure_name}')
            print(f'Role {adventure_role} created')

            # Create overwrites for the new category. All channels will be synced to these overwrites
            category_perms = dict()
            category_perms[adventure_role] = discord.PermissionOverwrite(view_channel=True)
            category_perms[discord.utils.get(ctx.guild.roles, name="Loremaster")] = discord.PermissionOverwrite(
                view_channel=True
            )
            category_perms[discord.utils.get(ctx.guild.roles, name="Bots")] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
            )
            category_perms[ctx.guild.default_role] = discord.PermissionOverwrite(view_channel=False)

            ooc_overwrites = category_perms.copy()
            quester_role = discord.utils.get(ctx.guild.roles, name='Quester')
            ooc_overwrites[quester_role] = discord.PermissionOverwrite(view_channel=True)
            print('Done creating category permissions and OoC overwrites')

            # Add DMs to the role & let them manage messages in their channels
            for dm in dms:
                await dm.add_roles(adventure_role, reason=f'Creating adventure {adventure_name}')
                category_perms[dm] = discord.PermissionOverwrite(manage_messages=True)

            # Create category for the adventure
            new_adventure_category = await ctx.guild.create_category_channel(
                name=adventure_name,
                overwrites=category_perms,
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
                overwrites=ooc_overwrites,
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
    async def add(self, ctx, members: Greedy[discord.Member]):

        adventure = self.get_adventure(ctx)
        adventure_role = discord.utils.get(ctx.guild.roles, id=adventure['Adventure Role ID'])

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
    async def addroom(self, ctx, room_name: str):
        adventure = self.get_adventure(ctx)

        if str(ctx.author.id) not in get_dms(adventure):
            await ctx.send('Error: You are not a DM of this adventure')
        else:
            category = discord.utils.get(ctx.guild.categories, id=adventure['CategoryChannel ID'])
            new_room = await category.create_text_channel(room_name, reason=f'Additional adventure room created by '
                                                                            f'{ctx.author.name}')
            await ctx.send(f'Room {new_room.mention} successfully created by {ctx.author.mention}')
            await ctx.message.delete()

    @addroom.error
    async def addroom_errors(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send('Error: Command cannot be used via private messages')
        print(error)

    @adventure.command(
        name='edit_room',
        hidden=True  # Still in dev
    )
    @commands.has_role("Dungeon Master")
    async def edit_room(self, ctx, **options):
        adventure = self.get_adventure(ctx)
        adventure_category = discord.utils.get(ctx.guild.categories, id=adventure['CategoryChannel ID'])

        if str(ctx.author.id) not in get_dms(adventure):
            await ctx.send('Error: You are not a DM of this adventure, '
                           'or there is no adventure associated with this channel')
            return
        else:
            adventure_channel = ctx.channel

            if 'name' in options.keys():
                '''Changing the channel's name'''
                await ctx.channel.edit(name=str(options['name']))

            if 'public' in options.keys():
                '''Changing whether the channel is visible to the @Quester role or not'''
                if str(options['public']).lower() == 'false':
                    await ctx.channel.edit(sync_permissions=True)
                elif str(options['public']).lower() == 'false':
                    quester_role = discord.utils.get(ctx.guild.roles, name='Quester')
                    await ctx.channel.edit(overwrites={quester_role: discord.PermissionOverwrite(view_channel=True)})
                else:
                    await ctx.send('Error: Invalid value for option \'public\'')

            if 'pos' in options.keys():
                '''Messing around with the channel's position. 0 is the top position.'''
                if str(options['pos']).lower() == 'top':
                    await ctx.channel.edit(position=0)
                    for channel in adventure_category.channels:
                        if not (channel == adventure_channel):
                            await channel.edit(position=(channel.position + 1))
                elif str(options['pos']).lower() == 'up':
                    if adventure_channel.position == 0:
                        await ctx.send('Warning: Channel position already at 0. Skipping. '
                                       'Use `pos=top` if you wish to make this the new top channel.')
                    else:
                        current_pos = adventure_channel.position
                        positions = [x.position for x in adventure_category.channels if x != adventure_channel]
                        closest = min(positions, key=lambda x: (current_pos - x))  # Issue: This gets the *lowest*, which would be negative for channels below the current.
                        if closest > 0:
                            await adventure_channel.edit(position=(closest - 1))
                        else:
                            await ctx.send('Warning: ')



            await ctx.message.delete()

    @adventure.command(
        name='status',
        hidden=True  # Still in dev
    )
    async def adventure_status(self, ctx, members: Greedy[discord.Member] = None):
        adventure = self.get_adventure(ctx)
        adventure_role = discord.utils.get(ctx.guild.roles, id=adventure['Adventure Role ID'])
        if members:
            for member in members:
                if member not in adventure_role.members:
                    await ctx.send(f'Error: <{member.mention}> not found in <{adventure_role.name}>')
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

    def get_adventure(self, ctx):
        list_of_dicts = self.adventures_sheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
        adventure = next((item for item in list_of_dicts if item['CategoryChannel ID'] == ctx.channel.category_id),
                         None)
        return adventure
