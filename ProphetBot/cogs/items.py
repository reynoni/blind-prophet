import gspread
import os
import json
from discord.ext import commands
from ProphetBot.helpers import *
from texttable import Texttable
from timeit import default_timer as timer
import re
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
            print(f'match: {match}: {result_map[match]}')
            data = [match]
            data.extend(value for value in result_map[match][0:])
            # print(f'Adding row: {data}')
            table.add_row(data)

        output = '```' + table.draw() + '```'
    else:
        table.set_cols_align(["l", "r"])
        table.set_cols_valign(["m", "m"])
        table.set_cols_width([10, 20])
        table.header([headers[0], matches[0]])
        data = list(zip(headers[1:], (result_map[matches[0]])[0:]))
        table.add_rows(data, header=False)
        output = '`' + table.draw() + '`'

    return output


def sort_stock(stock):
    # reverse = None (Sorts in Ascending order)
    # key is set to sort using third element of
    # sublist lambda has been used
    return sorted(stock, key=lambda x: int(re.sub(r'\D+', '', x[2])))


class Items(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.weapons_map = dict()
        self.armor_map = dict()
        self.consumable_map = dict()
        self.scroll_map = dict()
        self.wondrous_map = dict()
        try:
            self.drive = gspread.service_account_from_dict(json.loads(os.environ['GOOGLE_SA_JSON']))
            self.inv_sheet = self.drive.open_by_key(os.environ["INV_SPREADSHEET_ID"])
            self.build_maps()
        except Exception as E:
            print(f'Exception: {type(E)} when trying to use service account')

        print(f'Cog \'Items\' loaded')

    @commands.command(aliases=['inv', 'i', 'roll'])
    async def inventory(self, ctx, shop_type, rarity, num=1, max_cost=1000000):
        print(f'Incoming \'Inventory\' command, args:\n'
              f'shop_type: {shop_type}\n'
              f'rarity: {rarity}\n'
              f'num: {num}')
        if shop_type.upper() not in SHOP_TYPES:
            await ctx.send(SHOP_TYPE_ERROR)
            return

        # We pass so many args directly from the command that this may as well be private within said command
        # def roll_stock(item_map, rarity_ind, cost_ind, max_qty):
        def roll_stock(item_map, max_qty):
            print(f'roll_stock, max_cost = {max_cost}')
            rarity_value = RARITY_MAP[rarity.upper()]
            available_items = list()
            item_stock = dict()
            for key in item_map.keys():
                parsed_cost = int(re.sub(r'\D+', '', item_map[key][1]))
                if parsed_cost <= max_cost:
                    item_rarity = item_map[key][0]
                    if RARITY_MAP[item_rarity.upper()] <= rarity_value:
                        # print(f'Found item \'{key}\' that matches rarity search \'{rarity_value}\'')
                        available_items.append(key)
                else:
                    print(f'Item \'{key}\' excluded for exceeding cost of {max_cost}')

            for i in range(num):
                rand_item = random.randint(0, len(available_items) - 1)
                item_name = available_items[rand_item]
                item_qty = random.randint(1, max_qty) if max_qty > 1 else 1

                if item_name in item_stock.keys():
                    item_stock[item_name] = item_stock[item_name] + item_qty
                else:
                    item_stock[item_name] = item_qty

            return item_stock

        # Set up Texttable for displaying results
        table = Texttable()
        table.set_cols_align(['l', 'c', 'l'])
        table.set_cols_valign(['m', 'm', 'm'])
        table.set_cols_width([20, 5, 7])

        if shop_type.upper() in ['BLACKSMITH', 'SMITH']:
            weapon_stock = roll_stock(self.weapons_map, max_qty=1)
            armor_stock = roll_stock(self.armor_map, max_qty=1)
            table.header(['Item', 'Qty', 'Cost'])

            weapon_data = []
            for item in weapon_stock:
                weapon_data.append([item, str(weapon_stock[item]), self.weapons_map[item][1]])
            table.add_rows(sort_stock(weapon_data), header=False)

            armor_data = []
            for item in armor_stock:
                armor_data.append([item, str(armor_stock[item]), self.armor_map[item][1]])
            table.add_rows(sort_stock(armor_data), header=False)

        elif shop_type.upper() in ['WEAPON', 'WEAPONS', 'WEAP']:
            weapon_stock = roll_stock(self.weapons_map, max_qty=1)
            table.header(['Item', 'Qty', 'Cost'])

            weapon_data = []
            for item in weapon_stock:
                weapon_data.append([item, str(weapon_stock[item]), self.weapons_map[item][1]])
            table.add_rows(sort_stock(weapon_data), header=False)

        elif shop_type.upper() in ['ARMOR', 'ARMORS', 'ARMOUR', 'ARMOURS', 'ARM']:
            armor_stock = roll_stock(self.armor_map, max_qty=1)
            table.header(['Item', 'Qty', 'Cost'])

            armor_data = []
            for item in armor_stock:
                armor_data.append([item, str(armor_stock[item]), self.armor_map[item][1]])
            table.add_rows(sort_stock(armor_data), header=False)

        elif shop_type.upper() in ['MAGIC', 'WONDROUS']:
            wondrous_stock = roll_stock(self.wondrous_map, max_qty=1)
            print(f'Magic Stock: {wondrous_stock}')
            table.header(['Item', 'Qty', 'Cost'])

            shop_data = []
            for item in wondrous_stock:
                shop_data.append([item, str(wondrous_stock[item]), self.wondrous_map[item][1]])
            table.add_rows(sort_stock(shop_data), header=False)

        elif shop_type.upper() in ['POTION', 'POTIONS', 'POT']:
            potion_stock = roll_stock(self.consumable_map, max_qty=4)
            print(f'Potion Stock: {potion_stock}')
            table.header(['Item', 'Qty', 'Cost'])

            potion_data = []
            for item in potion_stock:
                potion_data.append([item, str(potion_stock[item]), self.consumable_map[item][1]])
            if num > 1:  # Remove the first item and add the default healing potion in its place
                potion_data.pop()
                potion_data.append(['Potion of Healing', str(random.randint(1, 4)), '50'])
            table.add_rows(sort_stock(potion_data), header=False)

        elif shop_type.upper() in ['SCROLL', 'SCROLLS']:
            scroll_stock = roll_stock(self.scroll_map, max_qty=2)
            print(f'Scroll Stock: {scroll_stock}')
            table.header(['Item (lvl)', 'Qty', 'Cost'])

            scroll_data = []
            for item in scroll_stock:
                display_name = str(item) + ' (' + self.scroll_map[item][2] + ')'  # Appending the spell level
                scroll_data.append([display_name, str(scroll_stock[item]), self.scroll_map[item][1]])
            table.add_rows(sort_stock(scroll_data), header=False)

        output = '`' + table.draw() + '`'
        await ctx.send(output)
        await ctx.message.delete()

    @commands.command(aliases=['armour', 'arm'])
    async def armor(self, ctx, item_name):
        matches = [key for key in self.armor_map.keys() if item_name.lower() in key.lower()]
        if len(matches) == 0:
            await ctx.send(f'Error: Search query \"{item_name}\" returned no results.')
            return False
        elif len(matches) > 5:
            await ctx.send(f'Search \'{item_name}\' returned {len(matches)} results. Displaying top 5.')
            matches = matches[:5]

        table = build_table(matches, self.armor_map,
                            ['Item Name', 'Rarity', 'Price', 'Notes', 'Source'])

        await ctx.send(table)
        await ctx.message.delete()

    @commands.command(aliases=['weapons', 'weap'])
    async def weapon(self, ctx, item_name):
        matches = [key for key in self.weapons_map.keys() if item_name.lower() in key.lower()]
        if len(matches) == 0:
            await ctx.send(f'Error: Search query \"{item_name}\" returned no results.')
            return False
        elif len(matches) > 5:
            await ctx.send(f'Search \'{item_name}\' returned {len(matches)} results. Displaying top 5.')
            matches = matches[:5]

        print(f'{matches}')
        table = build_table(matches, self.weapons_map,
                            ['Item Name', 'Rarity', 'Price', 'Attunement', 'Notes', 'Source'])

        await ctx.send(table)
        await ctx.message.delete()

    @commands.command(aliases=['magic', 'wonderous'])
    async def wondrous(self, ctx, item_name):
        matches = [key for key in self.wondrous_map.keys() if item_name.lower() in key.lower()]
        if len(matches) == 0:
            await ctx.send(f'Error: Search query \"{item_name}\" returned no results.')
            return False
        elif len(matches) > 5:
            await ctx.send(f'Search \'{item_name}\' returned {len(matches)} results. Displaying top 5.')
            matches = matches[:5]

        print(f'{matches}')
        table = build_table(matches, self.wondrous_map,
                            ['Item Name', 'Rarity', 'Price', 'Attunement', 'Notes', 'Source'])

        await ctx.send(table)
        await ctx.message.delete()

    @commands.command(aliases=['consumable', 'pot'])
    async def potion(self, ctx, item_name):
        matches = [key for key in self.consumable_map.keys() if item_name.lower() in key.lower()]
        if len(matches) == 0:
            await ctx.send(f'Error: Search query \"{item_name}\" returned no results.')
            return False
        elif len(matches) > 5:
            await ctx.send(f'Search \'{item_name}\' returned {len(matches)} results. Displaying top 5.')
            matches = matches[:5]

        print(f'{matches}')
        table = build_table(matches, self.consumable_map, ['Item Name', 'Rarity', 'Price', 'Source'])

        await ctx.send(table)
        await ctx.message.delete()

    def build_maps(self):
        result_dict = self.inv_sheet.values_batch_get(list(['Weapons!A2:H', 'Armor!A2:H', 'Consumables!A2:E',
                                                            'Scrolls!A2:G', 'Wondrous!A2:F']))
        values_list = result_dict['valueRanges']  # This result is something beautiful

        self.weapons_map = {item[0]: item[1:] for item in values_list[0]['values']}
        self.armor_map = {item[0]: item[1:] for item in values_list[1]['values']}
        self.consumable_map = {item[0]: item[1:] for item in values_list[2]['values']}
        self.scroll_map = {item[0]: item[1:] for item in values_list[3]['values']}
        self.wondrous_map = {item[0]: item[1:] for item in values_list[4]['values']}
