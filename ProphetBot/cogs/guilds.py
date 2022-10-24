from discord import *
from ProphetBot.bot import BpBot
from discord.ext import commands

from ProphetBot.constants import THUMBNAIL
from ProphetBot.models.schemas import guild_schema
from ProphetBot.queries.guild_queries import get_guild, update_guild_settings, insert_new_guild
from ProphetBot.models.db_objects import BP_Guild

# TODO: Setup appropriate security checks

def setup(bot):
    bot.add_cog(Guilds(bot))

class GuildEmbed(Embed):
    def __init__(self, ctx: ApplicationContext, guild: BP_Guild):
        super().__init__(title=f'Server Settings for {ctx.guild.name}',
                         colour=Color.random())
        self.set_thumbnail(url=THUMBNAIL)

        self.add_field(name="**Settings**",
                       value=f"**Max Level:** {guild.max_level}\n"
                             f"**Max Rerolls:** {guild.max_reroll}",
                       inline=False)

        self.add_field(name="Moderator/Magewright Roles",
                       value="\n".join([f"\u200b {r}" for r in guild.get_mod_role_names(ctx)]),
                       inline=False)

        self.add_field(name="Loremaster Roles",
                       value="\n".join([f"\u200b {r}" for r in guild.get_loremaster_role_names(ctx)]),
                       inline=False)

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
    async def set_max_reroll(self, ctx: ApplicationContext,
                             amount: Option(int, description="Max number of rerolls allowed", required=True,
                                            default=1)):
        """
        Used to set the max number of rerolls allowed on a guild

        :param ctx: Context
        :param amount: Max number of rerolls allowed
        """

        await ctx.defer()

        async with self.bot.db.acquire() as conn:
            results = await conn.execute(get_guild(ctx.guild_id))
            gRow = await results.first()

        if gRow is None:
            guild = BP_Guild(id=ctx.guild_id, max_level=1, server_xp=0, weeks=0, max_reroll=amount, mod_roles=[],
                             lore_roles=[])
            async with self.bot.db.acquire() as conn:
                await conn.execute(insert_new_guild(guild))

        else:
            guild: BP_Guild = guild_schema().load(gRow)
            guild.max_reroll=amount
            async with self.bot.db.acquire() as conn:
                await conn.execute(update_guild_settings(guild))

        await ctx.respond(embed=GuildEmbed(ctx, guild))


    @guilds_commands.command(
        name="max_level",
        description="Set the maximum character level for the server. Default is 1"
    )
    async def set_max_level(self, ctx: ApplicationContext,
                            amount: Option(int, description="Max character level", required=True,
                                           default=1)):
        """
        Used to set the maximum character level for a guild

        :param ctx: Context
        :param amount: Max character level
        """

        await ctx.defer()

        async with self.bot.db.acquire() as conn:
            results = await conn.execute(get_guild(ctx.guild_id))
            gRow = await results.first()

        if gRow is None:
            guild = BP_Guild(id=ctx.guild_id, max_level=amount, server_xp=0, weeks=0, max_reroll=1, mod_roles=[],
                             lore_roles=[])
            async with self.bot.db.acquire() as conn:
                await conn.execute(insert_new_guild(guild))

        else:
            guild: BP_Guild = guild_schema().load(gRow)
            guild.max_level = amount
            async with self.bot.db.acquire() as conn:
                await conn.execute(update_guild_settings(guild))

        await ctx.respond(embed=GuildEmbed(ctx, guild))


    @guilds_commands.command(
        name="add_mod_role",
        description="Add a mod/magewright role for the server"
    )
    async def add_mod_roles(self, ctx: ApplicationContext,
                            mod_role: Option(Role, description="Mod/Magewright role", required=True)):
        """
        :param ctx: Context
        :param mod_role: Role to add to the server mod role list
        """

        await ctx.defer()

        async with self.bot.db.acquire() as conn:
            results = await conn.execute(get_guild(ctx.guild_id))
            gRow = await results.first()

        if gRow is None:
            guild = BP_Guild(id=ctx.guild_id, max_level=1, server_xp=0, weeks=0, max_reroll=1,
                             mod_roles=[mod_role.id],
                             lore_roles=[])
            async with self.bot.db.acquire() as conn:
                await conn.execute(insert_new_guild(guild))

        else:
            guild: BP_Guild = guild_schema().load(gRow)
            guild.mod_roles.append(mod_role.id)
            async with self.bot.db.acquire() as conn:
                await conn.execute(update_guild_settings(guild))

        await ctx.respond(embed=GuildEmbed(ctx, guild))



