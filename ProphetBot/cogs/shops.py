import bisect
import logging
import random

from discord import SlashCommandGroup, ApplicationContext, Member, Option
from discord.ext import commands
from texttable import Texttable

from ProphetBot.bot import BpBot
from ProphetBot.helpers import get_character, create_logs, shop_type_autocomplete, get_or_create_guild, sort_stock
from ProphetBot.models.db_objects import PlayerCharacter, DBLog, PlayerGuild
from ProphetBot.models.embeds import ErrorEmbed, DBLogEmbed

log = logging.getLogger(__name__)


def setup(bot: commands.Bot):
    bot.add_cog(Shops(bot))


class Shops(commands.Cog):
    bot: BpBot
    shop_commands = SlashCommandGroup("shop", "Shop commands")

    def __init__(self, bot):
        self.bot = bot
        log.info(f'Cog \'Shops\' loaded')

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

        character: PlayerCharacter = await get_character(ctx.bot, player.id, ctx.guild_id)

        if character is None:
            return await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True)

        if character.gold < cost:
            return await ctx.respond(embed=ErrorEmbed(description=f"{player.mention} cannot afford the {cost}gp cost"))

        act = ctx.bot.compendium.get_object("c_activity", "BUY")

        log_entry: DBLog = await create_logs(ctx, character, act, item, -cost)

        await ctx.respond(embed=DBLogEmbed(ctx, log_entry, character))

    @shop_commands.command(
        name="sell",
        descrption="Logs the sale of an item from a player. Not for player establishment sales"
    )
    async def sell_log(self, ctx: ApplicationContext,
                       player: Option(Member, description="Player who bought the item", required=True),
                       item: Option(str, description="The item being sold", required=True),
                       cost: Option(int, description="The cost of the item", min_value=0, max_value=999999,
                                    required=True)):
        await ctx.defer()

        character: PlayerCharacter = await get_character(ctx.bot, player.id, ctx.guild_id)

        if character is None:
            return await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True)

        act = ctx.bot.compendium.get_object("c_activity", "SELL")

        log_entry: DBLog = await create_logs(ctx, character, act, item, cost)

        await ctx.respond(embed=DBLogEmbed(ctx, log_entry, character))

    @shop_commands.command(
        name="inventory",
        description="Roll inventory"
    )
    async def item_inventory(self, ctx: ApplicationContext,
                             inventory_type: Option(str, description="Inventory type to roll",
                                                    autocomplete=shop_type_autocomplete,
                                                    required=True),
                             quantity: Option(int, description="Item quantities", required=True, default=1),
                             max_cost: Option(int, description="Max cost of items", required=True, default=1000000)):

        g: PlayerGuild = await get_or_create_guild(ctx.bot.db, ctx.guild_id)

        if not (shop := ctx.bot.compendium.get_object("c_shop_type", inventory_type)):
            if inventory_type.upper() in ['SCROLL', 'SCROLLS']:
                shop = 'SCROLL'
            elif inventory_type.upper() in ['POTION', 'POTIONS']:
                shop = 'POTION'
            elif inventory_type.upper() in [x.upper() for x in list(ctx.bot.compendium.c_blacksmith_type[1].keys())]:
                shop = inventory_type.upper()
            else:
                shop = next((s.value.upper() for s in list(ctx.bot.compendium.c_shop_type[0].values()) if
                             inventory_type in s.synonyms), None)
        else:
            shop = shop.value.upper()

        if shop is None:
            return await ctx.respond(f"Error: Shop Type not found")

        def roll_stock(items: [], max_qty: int, num_offset: int = 0):
            rarity_value = bisect.bisect(list(ctx.bot.compendium.c_shop_tier[0].keys()), g.max_level)
            if len(items) == 0:
                return None
            elif hasattr(items[1], "seeking_only"):
                filtered_items = list(
                    filter(lambda i: i.cost <= max_cost and i.seeking_only is False and i.rarity.id <= rarity_value,
                           items))
            else:
                filtered_items = list(
                    filter(lambda i: i.cost <= max_cost and i.rarity.id <= rarity_value,
                           items))
            if len(filtered_items) == 0:
                return None

            stock = dict()

            if quantity - num_offset <= 0:
                return None

            for i in range(quantity - num_offset):
                rand_item = random.choice(filtered_items)
                qty = random.randint(1, max_qty if max_qty > 1 else 1)

                if rand_item.name in stock.keys():
                    stock[rand_item.name] = stock[rand_item.name] + qty
                else:
                    stock[rand_item.name] = qty

            return stock

        table = Texttable()
        table.set_cols_align(['l', 'c', 'l'])
        table.set_cols_valign(['m', 'm', 'm'])
        table.set_cols_width([20, 5, 7])

        if shop in ["BLACKSMITH", "WEAPON", "ARMOR"]:
            table.header(['Item', 'Qty', 'Cost'])

            if shop in ["BLACKSMITH", "WEAPON"]:
                weapon_type = ctx.bot.compendium.get_object("c_blacksmith_type", "Weapon")
                weapon_stock = roll_stock(
                    list(filter(lambda i: i.sub_type == weapon_type, list(ctx.bot.compendium.blacksmith[0].values()))),
                    max_qty=1)

                if weapon_stock is None:
                    return await ctx.respond(embed=ErrorEmbed(description="No items found matching parameters"),
                                             ephemeral=True)

                weapon_data = []
                for i in weapon_stock:
                    weapon = ctx.bot.compendium.get_object("blacksmith", i)
                    weapon_data.append([weapon.name, str(weapon_stock[i]), weapon.display_cost()])
                table.add_rows(sort_stock(weapon_data), header=False)

            if shop in ["BLACKSMITH", "ARMOR"]:
                armor_type = ctx.bot.compendium.get_object("c_blacksmith_type", "Armor")
                armor_stock = roll_stock(
                    list(filter(lambda i: i.sub_type == armor_type, list(ctx.bot.compendium.blacksmith[0].values()))),
                    max_qty=1)

                if armor_stock is None:
                    return await ctx.respond(embed=ErrorEmbed(description="No items found matching parameters"),
                                             ephemeral=True)

                armor_data = []
                for i in armor_stock:
                    armor = ctx.bot.compendium.get_object("blacksmith", i)
                    armor_data.append([armor.name, str(armor_stock[i]), armor.display_cost()])
                table.add_rows(sort_stock(armor_data), header=False)

        elif shop in ['CONSUMABLE', 'POTION']:
            table.header(['Item', 'Qty', 'Cost'])

            if quantity > 1:
                # healing_pots = list(filter(lambda i: 'healing' in i.name.lower(), self.consumable))
                # potion_stock = roll_stock(healing_pots, 4, 1)
                potion_stock = {'Potion of Healing': random.randint(1, 4)}
                potion_stock.update(roll_stock(list(ctx.bot.compendium.consumable[0].values()), 4, 1))
            else:
                potion_stock = roll_stock(list(ctx.bot.compendium.consumable[0].values()), 4)

            if potion_stock is None:
                return await ctx.respond(embed=ErrorEmbed(description="No items found matching parameters"),
                                         ephemeral=True)

            potion_data = []
            for p in potion_stock:
                if p == 'Potion of Healing':
                    potion_data.append([p, str(potion_stock[p]), '50'])
                else:
                    potion = ctx.bot.compendium.get_object("consumable", p)
                    potion_data.append([potion.name, str(potion_stock[p]), str(potion.cost)])

            table.add_rows(sort_stock(potion_data), header=False)

        elif shop in ['SCROLL']:
            table.header(['Item (lvl)', 'Qty', 'Cost'])

            scroll_stock = roll_stock(list(ctx.bot.compendium.scroll[0].values()), 2)

            if scroll_stock is None:
                return await ctx.respond(embed=ErrorEmbed(description="No items found matching parameters"),
                                         ephemeral=True)

            scroll_data = []

            for s in scroll_stock:
                scroll = ctx.bot.compendium.get_object("scroll", s)
                scroll_data.append([scroll.display_name(), str(scroll_stock[s]), str(scroll.cost)])

            table.add_rows(sort_stock(scroll_data), header=False)

        elif shop in ['MAGIC']:
            table.header(['Item', 'Qty', 'Cost'])

            magic_stock = roll_stock(list(ctx.bot.compendium.wondrous[0].values()), 1)

            if magic_stock is None:
                return await ctx.respond(embed=ErrorEmbed(description="No items found matching parameters"),
                                         ephemeral=True)

            magic_data = []
            for m in magic_stock:
                item = ctx.bot.compendium.get_object("wondrous", m)

                magic_data.append([item.name, str(magic_stock[m]), str(item.cost)])

            table.add_rows(sort_stock(magic_data), header=False)

        table_str = table.draw()

        async def _paginate(result: str):
            if len(result) > 1998:
                lines = result.split('\n')
                partial_table = '\n'.join(lines[:46])
                await ctx.send(f'`{partial_table}`')
                await _paginate('\n'.join(lines[46:]))
            else:
                await ctx.send(f'`{result}`')

        await _paginate(table_str)
        await ctx.delete()
