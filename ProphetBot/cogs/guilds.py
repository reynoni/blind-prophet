from discord import *
from ProphetBot.bot import BpBot
from discord.ext import commands
from timeit import default_timer as timer
from ProphetBot.helpers import get_or_create_guild, is_admin, get_weekly_stipend, create_logs
from ProphetBot.models.embeds import GuildEmbed, GuildStatus
from ProphetBot.models.schemas import CharacterSchema, RefWeeklyStipendSchema
from ProphetBot.queries import update_guild, get_characters, update_character, insert_weekly_stipend, \
    update_weekly_stipend, delete_weekly_stipend, get_guild_weekly_stipends, get_multiple_characters
from ProphetBot.models.db_objects import PlayerGuild, PlayerCharacter, RefWeeklyStipend, LevelCaps


# TODO: Setup appropriate security checks and update with the new get_or_create_guild function

def setup(bot: commands.Bot):
    bot.add_cog(Guilds(bot))


class Guilds(commands.Cog):
    bot: BpBot
    guilds_commands = SlashCommandGroup("guilds", "Commands related to guild specific settings")

    def __init__(self, bot):
        self.bot = bot
        print(f'Cog \'Guilds\' loaded')

    @guilds_commands.command(
        name="max_reroll",
        description="Set the max number of character rerolls. Default is 1"
    )
    @commands.check(is_admin)
    async def set_max_reroll(self, ctx: ApplicationContext,
                             amount: Option(int, description="Max number of rerolls allowed", required=True,
                                            default=1)):
        """
        Used to set the max number of rerolls allowed on a guild

        :param ctx: Context
        :param amount: Max number of rerolls allowed
        """

        await ctx.defer()

        g: PlayerGuild = await get_or_create_guild(ctx)

        g.max_reroll = amount
        async with self.bot.db.acquire() as conn:
            await conn.execute(update_guild(g))

        await ctx.respond(embed=GuildEmbed(ctx, g))

    @guilds_commands.command(
        name="max_level",
        description="Set the maximum character level for the server. Default is 3"
    )
    @commands.check(is_admin)
    async def set_max_level(self, ctx: ApplicationContext,
                            amount: Option(int, description="Max character level", required=True,
                                           default=3)):
        """
        Used to set the maximum character level for a guild

        :param ctx: Context
        :param amount: Max character level
        """

        await ctx.defer()

        g: PlayerGuild = await get_or_create_guild(ctx)
        g.max_level = amount
        async with self.bot.db.acquire() as conn:
            await conn.execute(update_guild(g))

        await ctx.respond(embed=GuildEmbed(ctx, g))

    @guilds_commands.command(
        name="status",
        description="Gets the current server's settings/status"
    )
    @commands.check(is_admin)
    async def guild_stats(self, ctx: ApplicationContext):
        """
        Displays the current server stats
        :param ctx: Context
        """
        await ctx.defer()

        g: PlayerGuild = await get_or_create_guild(ctx)

        await ctx.respond(embed=GuildStatus(ctx, g))

    @guilds_commands.command(
        name="add_stipend",
        description="Add/modify a role in the stipend list for weekly resets"
    )
    async def stipend_add(self, ctx: ApplicationContext,
                          role: Option(Role, description="Role to give a stipend for", required=True),
                          ratio: Option(float, description="Ratio of the stipend", required=True),
                          reason: Option(str, description="Reason for the stipend", required=False)):
        await ctx.defer()

        stipend: RefWeeklyStipend = await get_weekly_stipend(ctx.bot.db, role)

        if stipend is None:
            stipend = RefWeeklyStipend(role_id=role.id, ratio=ratio, guild_id=ctx.guild_id, reason=reason)
            async with ctx.bot.db.acquire() as conn:
                await conn.execute(insert_weekly_stipend(stipend))
        elif stipend.guild_id != ctx.guild_id:
            return await ctx.respond(f"Error: Stipend is not for this server")
        else:
            stipend.ratio = ratio
            stipend.reason = stipend.reason if reason is None else reason
            async with ctx.bot.db.acquire() as conn:
                await conn.execute(update_weekly_stipend(stipend))

        await ctx.respond(f"Stipend for @{role.name} at a ratio of {stipend.ratio} added/updated")

    @guilds_commands.command(
        name="remove_stipend",
        description="Remove a stipend"
    )
    async def stipend_remove(self, ctx: ApplicationContext,
                             role: Option(Role, description="Role to remove stipend for", required=True)):
        await ctx.defer()

        stipend: RefWeeklyStipend = await get_weekly_stipend(ctx.bot.db, role)

        if stipend is None:
            return await ctx.respond(f"No stipend for the given role")
        elif stipend.guild_id != ctx.guild_id:
            return await ctx.respond(f"Error: Stipend is not for this server")
        else:
            async with ctx.bot.db.acquire() as conn:
                await conn.execute(delete_weekly_stipend(stipend))

    @guilds_commands.command(
        name="weekly_reset",
        description="Performs a weekly reset for the server"
    )
    async def guild_weekly_reset(self, ctx: ApplicationContext):
        start = timer()
        g: PlayerGuild = await get_or_create_guild(ctx)
        guild_xp = g.week_xp
        player_xp = 0
        player_gold = 0
        slist = []

        g.server_xp += g.week_xp
        g.week_xp = 0
        g.weeks += 1

        async with ctx.bot.db.acquire() as conn:
            await conn.execute(update_guild(g))
            async for row in await conn.execute(get_characters(ctx.guild_id)):
                if row is not None:
                    character: PlayerCharacter = CharacterSchema(ctx.bot.compendium).load(row)
                    player_xp += character.div_xp
                    player_gold += character.div_gold
                    character.div_xp = 0
                    character.div_gold = 0
                    await conn.execute(update_character(character))

            print(f"Weekly stats for {ctx.guild.name}: Weekly Server XP = {guild_xp} | Player XP = {player_xp} |"
                  f" Player gold = {player_gold}")

            async for row in await conn.execute(get_guild_weekly_stipends(ctx.guild_id)):
                if row is not None:
                    stipend: RefWeeklyStipend = RefWeeklyStipendSchema().load(row)
                    slist.append(stipend)

        if len(slist) > 0:
            act: Activity = ctx.bot.compendium.get_object("c_activity", "STIPEND")
            for s in slist:
                players = [p.id for p in s.get_role(ctx).members]
                async with ctx.bot.db.acquire() as conn:
                    async for row in await conn.execute(get_multiple_characters(players, ctx.guild_id)):
                        if row is not None:
                            character: PlayerCharacter = CharacterSchema(ctx.bot.compendium).load(row)
                            cap: LevelCaps = ctx.bot.compendium.get_object("c_level_caps", character.get_level())
                            await create_logs(ctx, character, act, f"Stipend Role: {s.get_role(ctx).name} - {s.reason}",
                                              cap.max_gold * s.ratio)
        end = timer()

        await ctx.respond(f"Weekly reset complete in {end - start:.2f} seconds.")
