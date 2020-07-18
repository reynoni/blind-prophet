from attr import attrs
from discord.ext import commands
from os import listdir
from ProphetBot.helpers import *
from ProphetBot.localsettings import *
from ProphetBot.cogs.mod.gsheet import gsheet
from texttable import Texttable
import random


def setup(bot):
    bot.add_cog(Items(bot))


def build_table(matches, result_map, headers):
    table = Texttable()
    if len(matches) > 1:
        table.set_deco(Texttable.HEADER | Texttable.HLINES | Texttable.VLINES)
        table.set_cols_align(['c'] * len(headers))
        table.set_cols_valign(['c'] * len(headers))
        table.header(headers)

        for match in matches:
            data = [match]
            data.extend(value for value in result_map[match][1:])
            table.add_row(data)

        output = '```' + table.draw() + '```'
    else:
        table.set_cols_align(["l", "r"])
        table.set_cols_valign(["m", "m"])
        data = [(headers[0], matches[0])]
        data.extend(list(zip(headers[1:], (result_map[matches[0]])[1:])))
        table.add_rows(data)
        output = '`' + table.draw() + '`'

    return output


def roll_stock(item_map, rarity, num):
    print('roll_stock')
    rarity_value = RARITY_MAP[rarity.upper()]
    available_items = list()
    item_stock = dict()

    for key in item_map.keys():
        item_rarity = item_map[key][1]
        if RARITY_MAP[item_rarity.upper()] <= rarity_value:
            print(f'Found item \'{key}\' that matches rarity search \'{rarity_value}\'')
            available_items.append(key)
    print(f'Available Items: {available_items}')
    for i in range(int(num)):
        rand_num = random.randint(0, len(available_items) - 1)
        print(f'rand_hum = {rand_num}')
        item_name = available_items[rand_num]
        if item_name in item_stock.keys():
            item_stock[item_name] = item_stock[item_name] + 1
        else:
            item_stock[item_name] = 1

    return item_stock


def sort_stock(stock):
    # reverse = None (Sorts in Ascending order)
    # key is set to sort using third element of
    # sublist lambda has been used
    return sorted(stock, key=lambda x: int(x[2]))


class Items(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.sheet = gsheet()
        self.weapons_map = self.build_map(WEAP_ARM_SPREADSHEET_ID, 'Weapons!B2:H')
        print(f'Weapon Map: {self.weapons_map}')
        self.armor_map = self.build_map(WEAP_ARM_SPREADSHEET_ID, 'Armor!B2:H')
        self.consumable_map = dict()
        self.scroll_map = dict()
        self.wondrous_map = self.build_map(MAGIC_ITEM_SPREADSHEET_ID, 'Sheet1!C3:I')

        print(f'Cog \'items\' loaded')

    @commands.command()
    async def inventory(self, ctx, shop_type, rarity, num):
        print(f'Incoming \'Inventory\' command, args:\n'
              f'shop_type: {shop_type}\n'
              f'rarity: {rarity}\n'
              f'num: {num}')
        if shop_type.upper() not in ['BLACKSMITH', 'CONSUMABLE', 'MAGIC']:
            print('Error, shop type not right')
            return
        print(f'SHOP TYPE = {shop_type}')
        table = Texttable()
        if shop_type.upper() == 'BLACKSMITH':
            print('Getting blacksmith stuff')
            weapon_stock = roll_stock(self.weapons_map, rarity, num)
            print(weapon_stock)
            armor_stock = roll_stock(self.armor_map, rarity, num)
            table.set_cols_align(['l', 'c', 'c'])
            table.set_cols_valign(['m', 'm', 'm'])
            table.header(['Item', 'Qty', 'Cost'])
            for item in weapon_stock:
                table.add_row([item, str(weapon_stock[item]), self.weapons_map[item][5]])
            for item in armor_stock:
                table.add_row([item, str(armor_stock[item]), self.armor_map[item][5]])

        elif shop_type.upper() == 'MAGIC':
            print('Getting magic stuff')
            wondrous_stock = roll_stock(self.wondrous_map, rarity, num)
            print(wondrous_stock)
            table.set_cols_align(['l', 'c', 'c'])
            table.set_cols_valign(['m', 'm', 'm'])
            table.header(['Item', 'Qty', 'Cost'])
            # rows = [['Item', 'Qty', 'Cost']]
            shop_data = []
            for item in wondrous_stock:
                shop_data.append([item, str(wondrous_stock[item]), self.wondrous_map[item][5]])
            # rows.extend(sort_stock(shop_data))
            table.add_rows(sort_stock(shop_data), header=False)  # Header needs to be false if there is a header...

        output = '`' + table.draw() + '`'
        await ctx.send(output)
        await ctx.message.delete()

    @commands.command()
    @commands.check(is_tracker)
    async def armor(self, ctx, item_name):
        matches = [key for key in self.armor_map.keys() if item_name.lower() in key.lower()]
        if len(matches) > 5:
            await ctx.send(f'Search \'{item_name}\' returned {len(matches)} results. Displaying top 5.')
            matches = matches[:5]

        table = build_table(matches, self.armor_map, ['Item Name', 'Rarity', 'Attunement', 'Notes', 'Source', 'Price'])

        await ctx.send(table)
        await ctx.message.delete()

    @commands.command()
    @commands.check(is_tracker)
    async def weapon(self, ctx, item_name):
        matches = [key for key in self.wondrous_map.keys() if item_name.lower() in key.lower()]
        if len(matches) > 5:
            await ctx.send(f'Search \'{item_name}\' returned {len(matches)} results. Displaying top 5.')
            matches = matches[:5]

        print(f'{matches}')
        table = build_table(matches, self.wondrous_map, ['Item Name', 'Price', 'Attunement', 'Notes', 'Source', 'Rarity'])

        await ctx.send(table)
        await ctx.message.delete()

    @commands.command()
    @commands.check(is_tracker)
    async def wondrous(self, ctx, item_name):
        matches = [key for key in self.weapons_map.keys() if item_name.lower() in key.lower()]
        if len(matches) > 5:
            await ctx.send(f'Search \'{item_name}\' returned {len(matches)} results. Displaying top 5.')
            matches = matches[:5]

        print(f'{matches}')
        table = build_table(matches, self.weapons_map,
                            ['Item Name', 'Rarity', 'Attunement', 'Notes', 'Source', 'Price'])

        await ctx.send(table)
        await ctx.message.delete()

    def build_map(self, sheet_id, sheet_range):
        result_list = self.sheet.get(sheet_id, sheet_range, "FORMATTED_VALUE")
        result_list = result_list['values']
        print(f'{result_list}')
        return {  # Using fancy dictionary comprehension to make the dict
            item[0]: item[1:] for item in result_list
        }
    #
    # def update_weapon_map(self):
    #     XPLIST_RANGE = 'Weapons!A2:H'
    #     weapons_list = self.sheet.get(WEAP_ARM_SPREADSHEET_ID, XPLIST_RANGE, "FORMATTED_VALUE")
    #     weapons_list = weapons_list['values']
    #     print(f'{weapons_list}')
    #     return {  # Using fancy dictionary comprehension to make the dict
    #         weapon[1]: list(weapon[0], weapon[2:]) for weapon in weapons_list
    #     }
