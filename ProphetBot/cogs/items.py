import asyncio
import bisect
import random
from typing import List
from timeit import default_timer as timer

from discord import SlashCommandGroup, ApplicationContext, Option
from discord.ext import commands
from texttable import Texttable

from ProphetBot.bot import BpBot
from ProphetBot.helpers import shop_type_autocomplete, get_or_create_guild, sort_stock, item_autocomplete
from ProphetBot.models.db_objects import PlayerGuild
from ProphetBot.models.db_objects.item_objects import ItemBlacksmith
from ProphetBot.models.embeds import BlacksmithItemEmbed, MagicItemEmbed, ConsumableItemEmbed, ScrollItemEmbed
from ProphetBot.models.schemas.item_schema import ItemBlacksmithSchema, ItemWondrousSchema, ItemConsumableSchema, \
    ItemScrollSchema
from ProphetBot.queries import get_blacksmith_items, get_wondrous_items, get_consumable_items, get_scroll_items


def setup(bot: commands.Bot):
    bot.add_cog(Items(bot))


class Items(commands.Cog):
    bot: BpBot
    item_commands = SlashCommandGroup("item", "Item commands")

    # noinspection PyTypeHints
    def __init__(self, bot):
        self.bot = bot
        print(f'Cog \'Items\' loaded')

    @item_commands.command(
        name="lookup",
        description="Look up item information"
    )
    async def item_lookup(self, ctx: ApplicationContext,
                          item: Option(str, description="Item to lookup",
                                       autocomplete=item_autocomplete,
                                       required=True)):

        if item_record := ctx.bot.compendium.get_object("blacksmith", item):
            embed = BlacksmithItemEmbed(item_record)
        elif item_record := ctx.bot.compendium.get_object("wondrous", item):
            embed = MagicItemEmbed(item_record)
        elif item_record := ctx.bot.compendium.get_object("consumable", item):
            embed = ConsumableItemEmbed(item_record)
        elif item_record := ctx.bot.compendium.get_object("scroll", item):
            embed = ScrollItemEmbed(item_record)
        else:
            await ctx.respond(f"Item not found")

        await ctx.respond(embed=embed)
