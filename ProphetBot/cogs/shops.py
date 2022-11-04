from discord import SlashCommandGroup, ApplicationContext, Member, Option
from discord.ext import commands
from ProphetBot.bot import BpBot
from ProphetBot.helpers import get_character, create_logs
from ProphetBot.models.db_objects import PlayerCharacter, DBLog
from ProphetBot.models.embeds import ErrorEmbed, LogEmbed, DBLogEmbed


def setup(bot: commands.Bot):
    bot.add_cog(Shops(bot))


class Shops(commands.Cog):
    bot: BpBot
    shop_commands = SlashCommandGroup("shop", "Shop commands")

    def __init__(self, bot):
        self.bot = bot
        print(f'Cog \'Shops\' loaded')

    @shop_commands.command(
        name="buy",
        description="Logs the sale of an item to a player"
    )
    async def buy_log(self, ctx: ApplicationContext,
                      player: Option(Member, description="Player who bought the item", required=True),
                      item: Option(str, description="The item being bought", required=True),
                      cost: Option(int, description="The cost of the item", min_value=0, max_value=999999,
                                   required=True)):

        await ctx.defer()

        character: PlayerCharacter = await get_character(ctx, player.id, ctx.guild.id)

        if character is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            return await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True)

        if character.gold < cost:
            return await ctx.respond(embed=ErrorEmbed(description=f"{player.mention} cannot afford the {cost}go cost"))

        act = ctx.bot.compendium.get_object("c_activity", "BUY")

        log_entry: DBLog = await create_logs(ctx, character, act, item, -cost)

        await ctx.respond(embed=DBLogEmbed(ctx, log_entry, character))

    @shop_commands.command(
        name="sell",
        descrption="Logs the sale of an item from a player. Not for player establishment sales"
    )
    async def sell_log(self, ctx: ApplicationContext,
                      player: Option(Member, description="Player who bought the item", required=True),
                      item: Option(str, description="The item being bought", required=True),
                      cost: Option(int, description="The cost of the item", min_value=0, max_value=999999,
                                   required=True)):
        await ctx.defer()

        character: PlayerCharacter = await get_character(ctx, player.id, ctx.guild.id)

        if character is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            return await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True)

        act = ctx.bot.compendium.get_object("c_activity", "SELL")

        log_entry: DBLog = await create_logs(ctx, character, act, item, cost)

        await ctx.respond(embed=DBLogEmbed(ctx, log_entry, character))


