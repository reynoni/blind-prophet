import asyncio
import bisect
from statistics import mean
from typing import List

import aiopg.sa
import discord
from aiopg.sa.result import RowProxy
from discord import ButtonStyle, Embed, Member, Color, TextChannel
from discord.commands import SlashCommandGroup, Option, OptionChoice, permissions
from discord.commands.context import ApplicationContext
from discord.ext import commands, tasks
from discord.ui import Button
from sqlalchemy.engine import Row

from ProphetBot.bot import BpBot
from ProphetBot.constants import TIERS, MAX_PHASES
from ProphetBot.helpers import filter_characters_by_ids
from ProphetBot.models.embeds import ArenaStatusEmbed
from ProphetBot.models.sheets_objects import Character, ArenaEntry
from ProphetBot.queries import select_active_arena_by_channel, insert_new_arena, update_arena_tier, \
    update_arena_completed_phases, close_arena_by_id
from ProphetBot.sheets_client import GsheetsClient


def setup(bot):
    bot.add_cog(Arenas(bot))


def format_player_list(players: List[Member]):
    return "\n".join([f"-{p.mention}" for p in players])


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


async def update_status_embed(interaction: discord.Interaction, characters: List[Character], arena_row: RowProxy):
    """
    Does all the repeated filtering and formatting required to get an updated status embed

    :param interaction:
    :param characters: 
    :param arena_row:
    :return:
    """
    msg: discord.Message = await interaction.channel.fetch_message(arena_row.pin_message_id)

    host = filter_characters_by_ids(characters, [arena_row.host_id])[0]
    arena_role = discord.utils.get(interaction.guild.roles, id=arena_row.role_id)
    players = filter_characters_by_ids(characters,
                                       [m.id for m in arena_role.members if m.id != arena_row.host_id])

    embed = ArenaStatusEmbed(
        host=host,
        tier=arena_row.tier,
        completed_phases=arena_row.completed_phases,
        players=players
    )

    if msg:
        await msg.edit(embed=embed)


async def add_to_arena(interaction: discord.Interaction, player: Member, arena_row: RowProxy) -> List[int]:
    # Everything looks good, so we can add the user to the role and determine the tier
    channel_role = discord.utils.get(interaction.guild.roles, id=arena_row.role_id)
    members_in_arena = [m.id for m in channel_role.members if m.id != arena_row.host_id]

    await player.add_roles(channel_role, reason=f"Joining {interaction.channel.name}")
    members_in_arena.append(interaction.user.id)

    await interaction.response.send_message(f"{player.mention} has joined the arena!", ephemeral=False)
    await _remove_from_board(interaction, player)

    # Returning this value since role.members is cached and will not always reflect the true state of the role
    # immediately after granting the role to a member
    return members_in_arena


async def update_tier(arena_id: int, characters: List[Character], db: aiopg.sa.Engine, player_ids: List[int]):
    characters_in_arena = filter_characters_by_ids(characters, player_ids)
    tier = determine_tier(characters_in_arena)

    async with db.acquire() as conn:
        await conn.execute(update_arena_tier(arena_id=arena_id, new_tier=tier))


def determine_tier(characters: List[Character]):
    if len(characters) == 0:
        return 0
    average_level = mean([c.level for c in characters])
    return bisect.bisect(TIERS, average_level)


class JoinArenaView(discord.ui.View):
    db: aiopg.sa.Engine
    sheets_client: GsheetsClient

    def __init__(self, db: aiopg.sa.Engine, sheets_client: GsheetsClient):
        super().__init__(timeout=None)
        self.db = db
        self.sheets_client = sheets_client

    @discord.ui.button(label="Join Arena", custom_id="join_arena", style=ButtonStyle.primary)
    async def view_callback(self, button: Button, interaction: discord.Interaction):
        async with self.db.acquire() as conn:
            results = await conn.execute(select_active_arena_by_channel(interaction.channel_id))
            arena_row = await results.first()
        if not arena_row:
            await interaction.response.send_message(f"Error: No active arena present in this channel", ephemeral=True)
            return
        if not (channel_role := discord.utils.get(interaction.guild.roles, id=arena_row.role_id)):
            await interaction.response.send_message(f"Error: Role @{interaction.channel.name} doesn\'t exist. "
                                                    f"A Council member may need to create it.", ephemeral=True)
            return
        if discord.utils.get(channel_role.members, id=interaction.user.id):
            await interaction.response.send_message(
                f"Error: you are already a participant in this arena.",
                ephemeral=True)
            return

        players_in_arena = await add_to_arena(interaction, interaction.user, arena_row)
        all_characters = self.sheets_client.get_all_characters()
        await update_tier(arena_row.id, all_characters, self.db, players_in_arena)
        await update_status_embed(interaction, all_characters, arena_row)


class Arenas(commands.Cog):
    bot: BpBot  # Typing annotation for my IDE's sake
    arena_commands = SlashCommandGroup("arena", "Commands related to arena management.")

    class ArenaPhaseEmbed(Embed):
        def __init__(self, ctx: ApplicationContext, host: Character, participants: List[Character],
                     result: str, phase: int, tier: int):
            rewards = f"{host.get_member(ctx).mention}: `HOST`\n"
            bonus = (phase > MAX_PHASES[tier] / 2) and result == 'WIN'
            for player in participants:
                rewards += f"{player.get_member(ctx).mention}: `{result}`"
                rewards += ', `BONUS`\n' if bonus else '\n'

            super().__init__(
                title=f"Phase {phase} Complete!",
                description=f"Completed phases: **{phase} / {MAX_PHASES[tier]}**",
                color=discord.Color.random(),
            )
            self.set_thumbnail(
                url="https://cdn.discordapp.com/attachments/794989941690990602/972998353103233124/IMG_2177.jpg"
            )
            self.add_field(name="The following rewards have been applied:", value=rewards, inline=False)

    def __init__(self, bot):
        self.bot = bot
        print(f'Cog \'Arenas\' loaded')

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(3.0)
        self.bot.add_view(JoinArenaView(self.bot.db, self.bot.sheets))

    @arena_commands.command(
        name="status",
        description="Shows the current status of this arena"
    )
    async def arena_status(self, ctx: ApplicationContext):
        async with self.bot.db.acquire() as conn:
            results = await conn.execute(select_active_arena_by_channel(ctx.channel_id))
            arena_row = await results.first()
        if not arena_row:
            embed = Embed(title=f"{ctx.channel.name} Free",
                          description=f"There is no active arena in this channel. If you're a host, you can use"
                                      f"`/arena claim` to start an arena here.",
                          color=Color.random())
            await ctx.response.send_message(embed=embed, ephemeral=False)
            return
        if discord.utils.get(ctx.guild.roles, name=ctx.channel.name) is None:
            await ctx.respond(f'Error: Role @{ctx.channel.name} doesn\'t exist. '
                              f'A Council member may need to create it.', ephemeral=False)
            return

        await ctx.defer()
        all_characters = self.bot.sheets.get_all_characters()
        host = filter_characters_by_ids(all_characters, [arena_row.host_id])[0]
        arena_role = discord.utils.get(ctx.guild.roles, id=arena_row.role_id)
        players = filter_characters_by_ids(all_characters,
                                           [m.id for m in arena_role.members if m.id != arena_row.host_id])

        embed = ArenaStatusEmbed(
            host=host,
            tier=arena_row.tier,
            completed_phases=arena_row.completed_phases,
            players=players
        )

        await ctx.respond(embed=embed, ephemeral=False)

    @arena_commands.command(
        name="claim",
        description="Opens an arena in this channel and sets you as the host."
    )
    async def arena_claim(self, ctx: ApplicationContext):
        await ctx.defer()
        async with self.bot.db.acquire() as conn:
            results = await conn.execute(select_active_arena_by_channel(ctx.channel_id))
            arena_row = await results.first()
        # First check to see if there is already an active arena in this channel,
        # then check to see if the associated role exists
        if arena_row:
            await ctx.respond(f'Error: {ctx.channel.mention} is already in use.\n'
                              f'Use `/arena status` to check the current status of this room.')
            return
        if not (channel_role := discord.utils.get(ctx.guild.roles, name=ctx.channel.name)):
            await ctx.respond(f'Error: Role @{ctx.channel.name} doesn\'t exist. '
                              f'A Council member may need to create it.')
            return

        await ctx.user.add_roles(channel_role, reason=f"Claiming {ctx.channel.name}")

        all_characters = self.bot.sheets.get_all_characters()
        host = filter_characters_by_ids(all_characters, [ctx.author.id])[0]
        embed = ArenaStatusEmbed(
            host=host,
            tier=1,
            completed_phases=0,
            players=None
        )
        msg: discord.WebhookMessage = await ctx.respond(
            embed=embed,
            view=JoinArenaView(db=self.bot.db, sheets_client=self.bot.sheets))

        # Everything looks good, so we can create the arena record and pin the status
        # msg = await interaction.original_message()
        async with self.bot.db.acquire() as conn:
            await conn.execute(insert_new_arena(ctx.channel_id, msg.id, channel_role.id, ctx.user.id))
        await msg.pin(reason=f"Arena claimed by {ctx.user.name}")

    @arena_commands.command(
        name="add",
        description="Adds the specified player to the arena in this channel"
    )
    async def arena_add(self, ctx: ApplicationContext,
                        player: Option(Member, "The player to add", required=True)):
        async with self.bot.db.acquire() as conn:
            results = await conn.execute(select_active_arena_by_channel(ctx.channel_id))
            arena_row = await results.first()
        # Check to make sure the arena and role exist. Send an error message and abort if they don't
        if not arena_row:
            await ctx.response.send_message(f"Error: No active arena present in this channel", ephemeral=True)
            return
        if not (channel_role := discord.utils.get(ctx.guild.roles, id=arena_row.role_id)):
            await ctx.response.send_message(f"Error: Role @{ctx.channel.name} doesn\'t exist. "
                                            f"A Council member may need to create it.", ephemeral=True)
            return
        if discord.utils.get(channel_role.members, id=player.id):
            await ctx.response.send_message(
                f"Error: {player.mention} is already a participant in this arena.",
                ephemeral=True)
            return

        players_in_arena = await add_to_arena(ctx.interaction, player, arena_row)
        all_characters = self.bot.sheets.get_all_characters()
        await update_tier(arena_row.id, all_characters, self.bot.db, players_in_arena)
        await update_status_embed(ctx.interaction, all_characters, arena_row)

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
            await ctx.respond(f"Error: No active arena in this channel", ephemeral=True)
            return
        channel_role = discord.utils.get(ctx.guild.roles, id=arena_row.role_id)
        if not (discord.utils.get(channel_role.members, id=player.id)):
            await ctx.respond(f"Error: {player.mention} is not a participant in this arena.", ephemeral=True)
            return

        await player.remove_roles(channel_role, reason=f"Leaving {ctx.channel.name}")

        await ctx.defer()
        all_characters = self.bot.sheets.get_all_characters()
        # We only want to recalculate the tier if the arena hasn't started or is in the first phase
        if arena_row.completed_phases == 0:
            members_in_arena = [m.id for m in channel_role.members if m.id != arena_row.host_id]
            characters_in_arena = [c for c in all_characters if c.player_id in members_in_arena]
            new_tier = determine_tier(characters_in_arena)

            async with self.bot.db.acquire() as conn:
                await conn.execute(update_arena_tier(arena_row.id, new_tier))

        await ctx.respond(f"{player.mention} has been removed from the arena")
        await update_status_embed(ctx.interaction, all_characters, arena_row)

    @arena_commands.command(
        name="phase",
        description="Records the outcome of an arena phase"
    )
    async def arena_phase(self, ctx: ApplicationContext,
                          result: Option(str, "The result of the phase", required=True,
                                         choices=[OptionChoice("win", "WIN"), OptionChoice("loss", "LOSS")])):
        async with self.bot.db.acquire() as conn:
            results = await conn.execute(select_active_arena_by_channel(ctx.channel_id))
            arena_row = await results.first()
        if not arena_row:
            await ctx.response.send_message(f"Error: No active arena in this channel", ephemeral=True)
            return

        await ctx.defer()
        completed_phases = arena_row.completed_phases + 1
        all_characters = self.bot.sheets.get_all_characters()
        channel_role = discord.utils.get(ctx.guild.roles, id=arena_row.role_id)

        log_messages = []
        host: Character = discord.utils.get(all_characters, player_id=arena_row.host_id)
        bot_username = f"{self.bot.user.name}#{self.bot.user.discriminator}"
        log_messages.append(ArenaEntry(bot_username, host, "HOST"))

        participant_ids = [m.id for m in channel_role.members if m.id != host.player_id]
        participants = filter_characters_by_ids(all_characters, participant_ids)
        for player in participants:
            log_messages.append(ArenaEntry(bot_username, player, result))

        if completed_phases > (MAX_PHASES[arena_row.tier] / 2) and result == "WIN":
            for player in participants:
                log_messages.append(ArenaEntry(bot_username, player, "BONUS"))

        embed = self.ArenaPhaseEmbed(ctx, host, participants, result, completed_phases, arena_row.tier)

        # Everything is good, so we can finally commit the results
        self.bot.sheets.log_activities(log_messages)
        async with self.bot.db.acquire() as conn:
            await conn.execute(update_arena_completed_phases(arena_row.id, completed_phases))

        await ctx.respond(embed=embed)
        async with self.bot.db.acquire() as conn:
            results = await conn.execute(select_active_arena_by_channel(ctx.channel_id))
            arena_row = await results.first()
        await update_status_embed(ctx.interaction, all_characters, arena_row)
        if completed_phases >= MAX_PHASES[arena_row.tier] or result == "LOSS":
            await self.close_arena(ctx, arena_row, channel_role)

    @arena_commands.command(
        name="close",
        description="Closes out a finished arena",
    )
    async def arena_close(self, ctx: ApplicationContext):
        async with self.bot.db.acquire() as conn:
            results = await conn.execute(select_active_arena_by_channel(ctx.channel_id))
            arena_row = await results.first()
        if not arena_row:
            await ctx.response.send_message(f"Error: No active arena in this channel", ephemeral=True)
            return

        channel_role = discord.utils.get(ctx.guild.roles, id=arena_row.role_id)
        await self.close_arena(ctx, arena_row, channel_role)

    # --------------------------- #
    # Helper functions
    # --------------------------- #

    async def close_arena(self, ctx: ApplicationContext, arena_row: RowProxy, role: discord.Role):
        for member in role.members:
            await member.remove_roles(role, reason="Arena complete")

        async with self.bot.db.acquire() as conn:
            await conn.execute(close_arena_by_id(arena_row.id))

        msg: discord.Message = await ctx.channel.fetch_message(arena_row.pin_message_id)

        if msg:
            await msg.delete(reason="Closing arena")
        await ctx.respond("Arena closed. This channel is now free for use.")
