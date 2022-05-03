import asyncio
import bisect
from statistics import mean

import aiopg.sa
import discord
from discord import ButtonStyle, Embed, Member
from discord.commands import SlashCommandGroup, CommandPermission, Option, OptionChoice, permissions
from discord.commands.context import ApplicationContext
from discord.ext import commands
from discord.ui import Button

from ProphetBot.bot import BpBot
from ProphetBot.helpers import *
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
    if len(characters) == 0:
        return 0
    average_level = mean([c.level for c in characters])
    return bisect.bisect(TIERS, average_level)


class Arenas(commands.Cog):
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

    class ArenaPhaseEmbed(Embed):
        def __init__(self, ctx: ApplicationContext, host: Character, participants: List[Character],
                     result: str, phase: int, tier: int):
            rewards = f"{host.get_member(ctx).mention}: `HOST`\n"
            bonus = phase >= MAX_PHASES[tier] / 2
            for player in participants:
                rewards += f"{player.get_member(ctx).mention}: `{result}`"
                rewards += ', `BONUS`\n' if bonus else '\n'

            super().__init__(
                title=f"Phase {phase} Complete!",
                description=f"Completed phases: **{phase} / {MAX_PHASES[tier]}**",
                color=discord.Color.random(),
            )
            self.add_field(name="The following rewards have been applied:", value=rewards, inline=False)

    def __init__(self, bot):
        self.bot = bot
        print(f'Cog \'Arenas\' loaded')

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(0.5)
        self.bot.add_view(self.JoinArenaView(self.bot.db, self.bot.sheets))

    @arena_commands.command(
        name="status",
        description="Shows the current status of this arena"
    )
    async def arena_status(self, ctx: ApplicationContext):
        async with self.bot.db.acquire() as conn:
            results = await conn.execute(select_active_arena_by_channel(ctx.channel_id))
            arena_row = await results.first()

        embed = Embed(color=discord.Color.random(), title=f"{ctx.channel.name.title()} Status")

        if arena_row:
            host = discord.utils.get(ctx.guild.members, id=arena_row.host_id)
            channel_role = discord.utils.get(ctx.guild.roles, id=arena_row.role_id)
            players = [p for p in channel_role.members if p.id != host.id]
            embed.description = f"**Tier:** {arena_row.tier}\n" \
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
        default_permission=False
    )
    @permissions.has_any_role("Host", "Council")
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
        await add_to_arena(ctx.interaction, self.bot.db, self.bot.sheets, ctx.author)

    @discord.commands.permissions.has_role("Host")
    @arena_commands.command(
        name="add",
        description="Adds the specified player to the arena in this channel",
        default_permission=False
    )
    @permissions.has_any_role("Host", "Council")
    async def arena_add(self, ctx: ApplicationContext,
                        player: Option(Member, "The player to add", required=True)):
        await add_to_arena(ctx.interaction, self.bot.db, self.bot.sheets, player)

    @discord.commands.permissions.has_role("Host")
    @arena_commands.command(
        name="remove",
        description="Removes the specified player from the arena",
        default_permission=False
    )
    @permissions.has_any_role("Host", "Council")
    async def arena_remove(self, ctx: ApplicationContext,
                           player: Option(Member, "The player to remove", required=True)):
        async with self.bot.db.acquire() as conn:
            results = await conn.execute(select_active_arena_by_channel(ctx.channel_id))
            arena_row = await results.first()
        if not arena_row:
            await ctx.response.send_message(f"Error: No active arena in this channel", ephemeral=True)
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

    @discord.commands.permissions.has_any_role("Host", "Magewright", "Council")
    @arena_commands.command(
        name="phase",
        description="Records the outcome of an arena phase",
        default_permission=False
    )
    @permissions.has_any_role("Host", "Council")
    async def arena_phase(self, ctx: ApplicationContext,
                          result: Option(str, "The result of the phase", required=True,
                                         choices=[OptionChoice("Win", "WIN"), OptionChoice("Loss", "LOSS")])):
        async with self.bot.db.acquire() as conn:
            results = await conn.execute(select_active_arena_by_channel(ctx.channel_id))
            arena_row = await results.first()
        if not arena_row:
            await ctx.response.send_message(f"Error: No active arena in this channel", ephemeral=True)
            return

        completed_phases = arena_row.completed_phases + 1
        characters = self.bot.sheets.get_all_characters()
        channel_role = discord.utils.get(ctx.guild.roles, id=arena_row.role_id)

        log_messages = []
        host: Character = discord.utils.get(characters, player_id=arena_row.host_id)
        log_messages.append(ArenaEntry(self.bot.user.name, host, "HOST"))

        participant_ids = [m.id for m in channel_role.members if m.id != host.player_id]
        participants = characters_by_ids(characters, participant_ids)
        for player in participants:
            log_messages.append(ArenaEntry(self.bot.user.name, player, result))

        if completed_phases >= MAX_PHASES[arena_row.tier] / 2 and result == "WIN":
            for player in participants:
                log_messages.append(ArenaEntry(self.bot.user.name, player, "BONUS"))

        embed = self.ArenaPhaseEmbed(ctx, host, participants, result, completed_phases, arena_row.tier)

        # Everything is good, so we can finally commit the results
        self.bot.sheets.log_activities(log_messages)
        async with self.bot.db.acquire() as conn:
            await conn.execute(update_arena_completed_phases(arena_row.id, completed_phases))

        await ctx.response.send_message(embed=embed)
        if completed_phases >= MAX_PHASES[arena_row.tier] or result == "LOSS":
            await self.close_arena(ctx, arena_row.id)

    @discord.commands.permissions.has_any_role("Host", "Magewright", "Council")
    @arena_commands.command(
        name="close",
        description="Closes out a finished arena",
        default_permission=False
    )
    @permissions.has_any_role("Host", "Council")
    async def arena_close(self, ctx: ApplicationContext):
        async with self.bot.db.acquire() as conn:
            results = await conn.execute(select_active_arena_by_channel(ctx.channel_id))
            arena_row = await results.first()
        if not arena_row:
            await ctx.response.send_message(f"Error: No active arena in this channel", ephemeral=True)
            return

        await self.close_arena(ctx, arena_row.id)

    # --------------------------- #
    # Helper functions
    # --------------------------- #

    async def close_arena(self, ctx: ApplicationContext, arena_id: int):
        async with self.bot.db.acquire() as conn:
            await conn.execute(close_arena_by_id(arena_id))

        await ctx.respond("Arena closed. This channel is now free for use.")
