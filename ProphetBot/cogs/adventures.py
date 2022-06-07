import discord
from discord.ext import commands
from discord.ext.commands import Greedy

from ProphetBot.bot import BpBot
from ProphetBot.helpers import *


def setup(bot):
    # print('loading_cog')
    bot.add_cog(Adventures(bot))


def clean_room_name(room_name: str):
    return room_name.strip().replace(' ', '-')


def get_dms(adventure_dict):
    dms = adventure_dict.get('DMs', None)
    if dms:
        return str(dms).split(', ')
    else:
        return None


class Adventures(commands.Cog):
    bot: BpBot  # Typing annotation for my IDE's sake

    def __init__(self, bot):
        # Setting up some objects
        self.bot = bot

        print(f'Cog \'Adventures\' loaded')

    @commands.command()
    async def getoverwrites(self, ctx):
        print(ctx.channel.overwrites)

    @commands.group(
        name='adventure',
        aliases=['ad']
    )
    async def adventure(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(f'Missing subcommand for `{ctx.prefix}adventure`')
        # Todo: Maybe make this a way to check active adventures?

    @adventure.command(
        name='create',
        aliases=['c'],
        brief="Creates a new adventure",
        help='**@Council/Loremaster only**\n\n'
             'Creates a channel category and role for the adventure, as well as two private channels.'
             'Any number of DMs may be specified. These players will be rewarded as (co-)DMs by `a command to be '
             'added later` and will have access to administrative bot commands.\n\n'
             '*Args:*\n'
             '---`adventure_name`: The name of the adventure as it should show up in the category and channel names\n'
             '---`role_name`: The name of the Role to be created for adventure participants\n'
             '---`dms`: The DM(s) of the adventure, formatted as an @mention or as a Discord ID. '
             'Multiple DMs should each be separated by a space.\n'
             '\n'
             'Example usage: `>adventure create \"1 Beginner Adventure\" \"Beginners\" @DM1 @DM2`'
    )
    @commands.has_any_role('Council', 'Loremaster')
    async def create(self, ctx, adventure_name: str, role_name: str, dms: Greedy[discord.Member]):

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
            category_perms[adventure_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            if loremaster_role := discord.utils.get(ctx.guild.roles, name="Loremaster"):
                category_perms[loremaster_role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                )
            if lead_dm_role := discord.utils.get(ctx.guild.roles, name="Lead DM"):
                category_perms[lead_dm_role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                )
            if bots_role := discord.utils.get(ctx.guild.roles, name="Bots"):
                category_perms[bots_role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                )
            category_perms[ctx.guild.default_role] = discord.PermissionOverwrite(
                view_channel=False,
                send_messages=False
            )

            # Add DMs to the role & let them manage messages in their channels
            for dm in dms:
                await dm.add_roles(adventure_role, reason=f'Creating adventure {adventure_name}')
                category_perms[dm] = discord.PermissionOverwrite(manage_messages=True)

            quester_role = discord.utils.get(ctx.guild.roles, name='Quester')
            ic_overwrites = category_perms.copy()
            ic_overwrites[quester_role] = discord.PermissionOverwrite(
                view_channel=True
            )
            ooc_overwrites = category_perms.copy()
            ooc_overwrites[quester_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
            )
            print('Done creating category permissions and OoC overwrites')

            # Create category for the adventure
            new_adventure_category = await ctx.guild.create_category_channel(
                name=adventure_name,
                overwrites=category_perms,
                reason=f'Creating category for {adventure_name}'
            )

            # Create default channels (1 IC, 1 OOC)
            ic_channel = await ctx.guild.create_text_channel(
                name=adventure_name,
                category=new_adventure_category,
                overwrites=ic_overwrites,
                position=0,
                reason=f'Creating adventure {adventure_name} IC Room'
            )
            ooc_channel = await ctx.guild.create_text_channel(
                name=f'{adventure_name}-ooc',
                category=new_adventure_category,
                overwrites=ooc_overwrites,
                position=1,
                reason=f'Creating adventure {adventure_name} OOC Room'
            )

            # Join up the DMs' ids into a Sheets-friendly format & write the row
            dm_ids = ', '.join([str(dm.id) for dm in dms])
            self.bot.sheets.adventures_sheet.append_row(
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
        name='add',
        aliases=['a'],
        brief="Adds a player to an adventure",
        help='**Dungeon Master only**\n\n'
             'Adds a player to an adventure. This command must be run in a channel of the adventure they are being '
             'added to. Any number of Players may be specified.\n\n'
             '*Args:*\n'
             '---`players`: The player(s) to be added, formatted as an @mention or as a Discord ID. '
             'Multiple players should each be separated by a space.\n'
             '\n'
             'Example usage: `>adventure add @Player1 @Player2`'
    )
    async def add(self, ctx, players: Greedy[discord.Member]):

        adventure = self._get_adventure_by_channel(ctx)

        if str(ctx.author.id) not in get_dms(adventure):
            await ctx.send('Error: You are not a DM of this adventure, '
                           'or there is no adventure associated with this channel')
        else:
            adventure_role = discord.utils.get(ctx.guild.roles, id=adventure['Adventure Role ID'])
            for member in players:
                await member.add_roles(adventure_role, reason=f'{member.name} added to role {adventure_role.name} '
                                                              f'by {ctx.author.name}')
                await ctx.send(f'{member.mention} added to adventure `{adventure_role.name}`')
            await ctx.message.delete()

    @adventure.command(
        name='remove',
        aliases=['r'],
        brief="Removes a player from an adventure",
        help='**Dungeon Master only**\n\n'
             'Removes a player from an adventure. This command must be run in a channel of the adventure they are '
             'being removed from. Any number of Players may be specified.\n\n'
             '*Args:*\n'
             '---`players`: The player(s) to be removed, formatted as an @mention or as a Discord ID. '
             'Multiple players should each be separated by a space.\n'
             '\n'
             'Example usage: `>adventure remove @Player1 @Player2`'
    )
    async def remove(self, ctx, players: Greedy[discord.Member]):
        adventure = self._get_adventure_by_channel(ctx)

        if str(ctx.author.id) not in get_dms(adventure):
            await ctx.send('Error: You are not a DM of this adventure, '
                           'or there is no adventure associated with this channel')
        else:
            adventure_role = discord.utils.get(ctx.guild.roles, id=adventure['Adventure Role ID'])
            for member in players:
                if adventure_role in member.roles:
                    await member.remove_roles(adventure_role,
                                              reason=f'{member.name} removed from role {adventure_role.name}'
                                                     f' by {ctx.author.name}')
                    await ctx.send(f'{member.mention} removed from adventure `{adventure_role.name}`')
                else:
                    await ctx.send(f'Error: {member.mention} not found in role `{adventure_role.name}`')
            await ctx.message.delete()

    # @adventure.guild_only()
    @adventure.command(
        name='addroom',
        aliases=['ar'],
        brief="Adds a channel to an adventure",
        help='**Dungeon Master only**\n\n'
             'Adds a channel to this adventure category. The room name will be automatically formatted to Discord '
             'channel specifications.\n\n'
             '*Args:*\n'
             '---`room_name`: The name of the new room. Spaces will become dashes, and everything will be lowercase.\n'
             '\n'
             'Example usage: `>adventure addroom "99 Best Adventure Ever"`'
    )
    async def addroom(self, ctx, room_name: str):
        adventure = self._get_adventure_by_channel(ctx)

        if str(ctx.author.id) not in get_dms(adventure):
            await ctx.send('Error: You are not a DM of this adventure, '
                           'or there is no adventure associated with this channel')
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

    @adventure.group(
        name='room',
        brief="Command group for editing adventure channels",
        help='**Dungeon Master only**\n\n'
             'Command group for editing adventure channels.\n\n'
    )
    @commands.has_role("Dungeon Master")
    async def room(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(f'Missing or unrecognized subcommand for `{ctx.prefix}adventure room`')

    @room.command(
        name='name',
        aliases=['rename'],
        brief="Changes the name of a room",
        help='**Dungeon Master only**\n\n'
             'Changes the name of the channel this command is run in. The channel name will be automatically '
             'formatted to Discord channel specifications.\n\n'
             '*Args:*\n'
             '---`room_name`: The name of the new room. Spaces will become dashes, and everything will be lowercase.\n'
             '\n'
             'Example usage: `>adventure room name "99 Bestest Adventure Ever"`'
    )
    async def room_name(self, ctx, room_name: str):
        adventure = self._get_adventure_by_channel(ctx)

        if str(ctx.author.id) not in get_dms(adventure):
            await ctx.send('Error: You are not a DM of this adventure, '
                           'or there is no adventure associated with this channel')
            return
        else:
            await ctx.channel.edit(name=room_name)
            await ctx.send(f"Room name changed to {ctx.channel.mention}")
            await ctx.message.delete()

    @room.command(
        name='open',
        aliases=['show', 'public'],
        brief="Opens a channel for public viewing",
        help='**Dungeon Master only**\n\n'
             'Makes the current channel viewable by `@Quester`s.\n\n'
             '*Args:*\n'
             '**None**\n'
             '\n'
             'Example usage: `>adventure room show`'
    )
    async def room_public(self, ctx):
        adventure = self._get_adventure_by_channel(ctx)

        if str(ctx.author.id) not in get_dms(adventure):
            await ctx.send('Error: You are not a DM of this adventure, '
                           'or there is no adventure associated with this channel')
            return
        else:
            overwrites = ctx.channel.overwrites
            quester_role = discord.utils.get(ctx.guild.roles, name='Quester')
            if quester_role:
                overwrites[quester_role] = discord.PermissionOverwrite(view_channel=True)
                await ctx.channel.edit(overwrites=overwrites)
                await ctx.send(f"{ctx.channel.mention} is now viewable by the @Quester role")
                await ctx.message.delete()
            else:
                await ctx.send("Couldn't find @Quester role, weird")

    @room.command(
        name='close',
        aliases=['hide', 'private'],
        brief="Hides a channel from the public",
        help='**Dungeon Master only**\n\n'
             'Hides the current channel from `@Quester`s.\n\n'
             '*Args:*\n'
             '**None**\n'
             '\n'
             'Example usage: `>adventure room close`'
    )
    async def room_private(self, ctx):
        adventure = self._get_adventure_by_channel(ctx)

        if str(ctx.author.id) not in get_dms(adventure):
            await ctx.send('Error: You are not a DM of this adventure, '
                           'or there is no adventure associated with this channel')
            return
        else:
            await ctx.channel.edit(sync_permissions=True)
            await ctx.send(f"{ctx.channel.mention} is now hidden to @Questers")
            await ctx.message.delete()

    @room.command(
        name='move',
        aliases=['pos'],
        brief="Changes the position of a channel",
        help='**Dungeon Master only**\n\n'
             'Moves the current channel within the adventure category. This may make the channel list jittery for '
             'a moment, so please use this command sparingly.\n\n'
             '*Args:*\n'
             '---`position`: The operation you would like to perform on this room.\n'
             '------`top` or `t`: Makes this the top channel of the category.\n'
             '------`up` or `u`: Moves the channel up by one step.\n'
             '------`down` or `d`: Moves the channel down by one step.\n'
             '------`bot` or `b`: Makes this the bottom channel of the category.\n'
             '\n'
             'Example usage: `>adventure room move top`, `>adventure room move down`, etc'
    )
    async def room_move(self, ctx, position: str):
        adventure = self._get_adventure_by_channel(ctx)

        if str(ctx.author.id) not in get_dms(adventure):
            await ctx.send('Error: You are not a DM of this adventure, '
                           'or there is no adventure associated with this channel')
            return
        else:
            adventure_category = discord.utils.get(ctx.guild.categories, id=adventure['CategoryChannel ID'])
            channels = adventure_category.text_channels
            old_pos = channels.index(ctx.channel)
            '''Set up the channel's new position'''
            if position.lower() in ['top', 't']:
                if old_pos == 0:
                    await ctx.send('Error: Channel position already at top.')
                    return
                else:
                    new_pos = 0
            elif position.lower() in ['up', 'u']:
                if old_pos == 0:
                    await ctx.send('Error: Channel position already at top.')
                    return
                else:
                    new_pos = old_pos - 1
            elif position.lower() in ['down', 'd']:
                if old_pos == len(channels) - 1:
                    await ctx.send('Error: Channel already at the lowest position.')
                    return
                else:
                    new_pos = old_pos + 1
            elif position.lower() in ['bottom', 'bot', 'b']:
                if old_pos == len(channels) - 1:
                    await ctx.send('Error: Channel already at the lowest position.')
                    return
                else:
                    new_pos = len(channels) - 1
            else:
                await ctx.send(f"Error: `{position}` is not a valid value for option `{ctx.invoked_with}`.")
                return

            channels.insert(new_pos, channels.pop(old_pos))

            for index, channel in enumerate(channels):
                await channel.edit(position=index)

            await ctx.send(f"Channel {ctx.channel.mention} moved to position {new_pos + 1} of {len(channels)}")
            await ctx.message.delete()

    @adventure.command(
        name='get_order',
        hidden=True  # dev command
    )
    @commands.has_role('Council')
    async def get_order(self, ctx):
        self._get_channel_order(ctx.channel.category)

    @adventure.command(
        name='status',
        hidden=True  # Still in dev
    )
    async def adventure_status(self, ctx, members: Greedy[discord.Member] = None):
        adventure = self._get_adventure_by_channel(ctx)
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

    def _is_dm(self, adventure_role: discord.Role, author: discord.Member):
        list_of_dicts = self.bot.sheets.adventures_sheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
        adventure = next(item for item in list_of_dicts if item['Adventure Role ID'] == adventure_role.id)
        if str(author.id) in str(adventure['DMs']).split(', '):
            return True
        return False

    def _get_adventure_by_channel(self, ctx):
        list_of_dicts = self.bot.sheets.adventures_sheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
        adventure = next((item for item in list_of_dicts if item['CategoryChannel ID'] == ctx.channel.category_id),
                         None)
        return adventure

    def _get_channel_order(self, adventure_category: discord.CategoryChannel):
        channels = adventure_category.text_channels
        order = [(channel.name, channel.position) for channel in channels]
        print(order)
