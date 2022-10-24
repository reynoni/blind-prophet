from timeit import default_timer as timer
from typing import List

from discord.ext import tasks

from ProphetBot.models.db_objects.category_objects import *
from ProphetBot.models.schemas.category_schema import *
from ProphetBot.queries.category_queries import *


async def get_table_as_list(conn, query, obj, schema) -> List:
    ary = []
    async for row in conn.execute(query):
        val: obj = schema.load(row)
        ary.append(val)

    return ary


class Compendium(object):

    # noinspection PyTypeHints
    def __init__(self):
        self.c_rarity = []  # type: list[c_rarity]
        self.c_blacksmith_type = []  # type: list[c_blacksmith_type]
        self.c_consumable_type = []  # type: list[c_consumable_type]
        self.c_magic_school = []  # type: list[c_magic_school]
        self.c_character_class = []  # type: list[c_character_class]
        self.c_character_subclass = []  # type: list[c_character_subclass]
        self.c_character_race = []  # type: list[c_character_race]
        self.c_character_subrace = []  # type: list[c_character_subrace]
        self.c_global_modifier = []  # type: list[c_global_modifier]
        self.c_host_status = []  # type: list[c_host_status]
        self.c_arena_tier = []  # type: list[c_arena_tier]
        self.c_adventure_tier = []  # type: list[c_adventure_tier]
        self.c_shop_type = []  # type: list[c_shop_type]
        self.c_activity = []  # type: list[c_activity]
        self.c_faction = []  # type: list[c_faction]
        self.c_dashboard_type = []  # type: list[c_dashboard_type]
        self.c_level_caps = []  # type: list[c_level_caps]

    async def reload(self, bot):
        print(f'Reloading data')
        start = timer()

        if bot.db is None:
            return

        async with bot.db.acquire() as conn:
            self.c_rarity = await get_table_as_list(conn, get_c_rarity(), c_rarity, c_rarity_schema())
            self.c_blacksmith_type = await get_table_as_list(conn, get_c_blacksmith_type(), c_blacksmith_type,
                                                                  c_blacksmith_type_schema())
            self.c_consumable_type = await get_table_as_list(conn, get_c_consumable_type(), c_consumable_type,
                                                                  c_consumable_type_schema())
            self.c_magic_school = await get_table_as_list(conn, get_c_magic_school(), c_magic_school,
                                                               c_magic_school_schema())
            self.c_character_class = await get_table_as_list(conn, get_c_character_class(), c_character_class,
                                                                  c_character_class_schema())
            self.c_character_subclass = await get_table_as_list(conn, get_c_character_subclass(),
                                                                     c_character_subclass, c_character_subclass_schema())
            self.c_character_race = await get_table_as_list(conn, get_c_character_race(), c_character_race,
                                                                 c_character_race_schema())
            self.c_character_subrace = await get_table_as_list(conn, get_c_character_subrace(), c_character_subrace,
                                                                    c_character_subrace_schema())
            self.c_global_modifier = await get_table_as_list(conn, get_c_global_modifier(), c_global_modifier,
                                                                  c_global_modifier_schema())
            self.c_host_status = await get_table_as_list(conn, get_c_host_status(), c_host_status,
                                                              c_host_status_schema())
            self.c_arena_tier = await get_table_as_list(conn, get_c_arena_tier(), c_arena_tier, c_arena_tier_schema())
            self.c_adventure_tier = await get_table_as_list(conn, get_c_adventure_tier(), c_adventure_tier,
                                                            c_adventure_tier_schema())
            self.c_shop_type = await get_table_as_list(conn, get_c_shop_type(), c_shop_type, c_shop_type_schema())
            self.c_activity = await get_table_as_list(conn, get_c_activity(), c_activity, c_activity_schema())
            self.c_faction = await get_table_as_list(conn, get_c_faction(), c_faction, c_faction_schema())
            self.c_dashboard_type = await get_table_as_list(conn, get_c_dashboard_type(), c_dashboard_type,
                                                            c_dashboard_type_schema())
            self.c_level_caps = await get_table_as_list(conn, get_c_level_caps(), c_level_caps, c_level_caps_schema())



        end = timer()
        print(f'Time to reload Compendium [ {end - start} ]')
