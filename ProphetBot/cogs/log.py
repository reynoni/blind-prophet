from discord import SlashCommandGroup, Option, ApplicationContext, Member, Role
from discord.ext import commands

from ProphetBot.helpers import get_character, create_logs, get_adventure_from_role
from ProphetBot.bot import BpBot
from ProphetBot.models.db_objects import PlayerCharacter, Activity, DBLog, Adventure, LevelCaps
from ProphetBot.models.embeds import ErrorEmbed, HxLogEmbed, LogEmbed, DBLogEmbed, AdventureEPEmbed
from ProphetBot.models.schemas import LogSchema, CharacterSchema
from ProphetBot.queries import get_n_player_logs, get_multiple_characters, update_adventure


def setup(bot: commands.Bot):
    bot.add_cog(Log(bot))


class Log(commands.Cog):
    bot: BpBot
    log_commands = SlashCommandGroup("log", "Logging commands for the magewrongs")

    def __init__(self, bot):
        self.bot = bot
        print(f'Cog \'Log\' loaded')

    @log_commands.command(
        name="get_history",
        description="Get the last weeks worth of logs for a player"
    )
    async def get_log_hx(self, ctx: ApplicationContext,
                         player: Option(Member, description="Player to get logs for", required=True),
                         num_logs: Option(int, description="Number of logs to get",
                                          min_value=1, max_value=20, default=5)):
        await ctx.defer()

        character: PlayerCharacter = await get_character(ctx, player.id, ctx.guild.id)

        if character is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            return await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True)

        log_ary = []

        async with self.bot.db.acquire() as conn:
            async for row in conn.execute(get_n_player_logs(character.id, num_logs)):
                if row is not None:
                    log: DBLog = LogSchema(ctx).load(row)
                    log_ary.append(log)

        await ctx.respond(embed=HxLogEmbed(log_ary, character, ctx), ephemeral=True)

    @log_commands.command(
        name="rp",
        description="Logs a completed RP"
    )
    async def rp_log(self, ctx: ApplicationContext,
                     player: Option(Member, description="Player who participated in the RP", required=True)):
        await ctx.defer()

        character: PlayerCharacter = await get_character(ctx, player.id, ctx.guild.id)

        if character is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            return await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True)

        act: Activity = ctx.bot.compendium.get_object("c_activity", "RP")

        log_entry = await create_logs(ctx, character, act)

        await ctx.respond(embed=DBLogEmbed(ctx, log_entry, character))

    @log_commands.command(
        name="bonus",
        description="Give bonus gold and/or xp to a player"
    )
    async def bonus_log(self, ctx: ApplicationContext,
                        player: Option(Member, description="Player receiving the bonus", required=True),
                        reason: Option(str, description="The reason for the bonus", required=True),
                        gold: Option(int, description="The amount of gold", default=0, min_value=0, max_value=2000),
                        xp: Option(int, description="The amount of xp", default=0, min_value=0, max_value=150)):
        await ctx.defer()

        character: PlayerCharacter = await get_character(ctx, player.id, ctx.guild.id)

        if character is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            return await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True)

        act: Activity = ctx.bot.compendium.get_object("c_activity", "BONUS")

        log_entry = await create_logs(ctx, character, act, reason, gold, xp)

        await ctx.respond(embed=DBLogEmbed(ctx, log_entry, character))

    @log_commands.command(
        name="ep",
        description="Grants adventure rewards to the players of a given adventure role"
    )
    async def ep_log(self, ctx: ApplicationContext,
                     role: Option(Role, description="The adventure role to get rewards", required=True),
                     ep: Option(int, description="The number of EP to give rewards for")):
        await ctx.defer()

        adventure: Adventure = await get_adventure_from_role(ctx, role.id)

        if adventure is None:
            return await ctx.respond(embed=ErrorEmbed(description=f"No adventure found for {role.mention}"),
                                     ephemeral=True)
        elif len(role.members) == 0:
            return await ctx.respond(embed=ErrorEmbed(description=f"Role {role.mention} has no members. Aborting."),
                                     ephemeral=True)

        players = [p.id for p in role.members]
        adventure.ep += ep

        char_act: Activity = ctx.bot.compendium.get_object("c_activity", "ADVENTURE")
        dm_act: Activity = ctx.bot.compendium.get_object("c_activity", "ADVENTURE_DM")

        async with ctx.bot.db.acquire() as conn:
            await conn.execute(update_adventure(adventure))
            async for row in await conn.execute(get_multiple_characters(players, ctx.guild.id)):
                if row is not None:
                    character: PlayerCharacter = CharacterSchema(ctx.bot.compendium).load(row)
                    cap: LevelCaps = ctx.bot.compendium.get_object("c_level_caps", character.get_level())
                    ratio = char_act.ratio if character.player_id not in adventure.dms else dm_act.ratio
                    await create_logs(ctx, character, char_act, adventure.name, (cap.max_gold * ratio) * ep)

        await ctx.respond(embed=AdventureEPEmbed(ctx, adventure, ep))
