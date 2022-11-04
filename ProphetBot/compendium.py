import asyncio
import os
from timeit import default_timer as timer
from typing import List

from discord import Bot
from discord.ext import tasks

from ProphetBot.models.schemas.category_schema import *
from ProphetBot.queries.category_queries import *


async def get_table_as_list(conn, query, obj, schema) -> List:
    ary = []
    async for row in conn.execute(query):
        val: obj = schema.load(row)
        ary.append(val)

    return ary


class Compendium:

    # noinspection PyTypeHints
    def __init__(self):
        self.c_rarity = []  # type: list[Rarity]
        self.c_blacksmith_type = []  # type: list[BlacksmithType]
        self.c_consumable_type = []  # type: list[ConsumableType]
        self.c_magic_school = []  # type: list[MagicSchool]
        self.c_character_class = []  # type: list[CharacterClass]
        self.c_character_subclass = []  # type: list[CharacterSubclass]
        self.c_character_race = []  # type: list[CharacterRace]
        self.c_character_subrace = []  # type: list[CharacterSubrace]
        self.c_global_modifier = []  # type: list[GlobalModifier]
        self.c_host_status = []  # type: list[HostStatus]
        self.c_arena_tier = []  # type: list[ArenaTier]
        self.c_adventure_tier = []  # type: list[AdventureTier]
        self.c_adventure_rewards = []  # type: list[AdventureRewards]
        self.c_shop_type = []  # type: list[ShopType]
        self.c_activity = []  # type: list[Activity]
        self.c_faction = []  # type: list[Faction]
        self.c_dashboard_type = []  # type: list[DashboardType]
        self.c_level_caps = []  # type: list[LevelCaps]

    async def reload(self, bot):
        print(f'Reloading data')
        start = timer()

        if not hasattr(bot, "db"):
            return

        async with bot.db.acquire() as conn:
            self.c_rarity = await get_table_as_list(conn, get_c_rarity(), Rarity, RaritySchema())
            self.c_blacksmith_type = await get_table_as_list(conn, get_c_blacksmith_type(), BlacksmithType,
                                                             BlacksmithTypeSchema())
            self.c_consumable_type = await get_table_as_list(conn, get_c_consumable_type(), ConsumableType,
                                                             ConsumableTypeSchema())
            self.c_magic_school = await get_table_as_list(conn, get_c_magic_school(), MagicSchool,
                                                          MagicSchoolSchema())
            self.c_character_class = await get_table_as_list(conn, get_c_character_class(), CharacterClass,
                                                             CharacterClassSchema())
            self.c_character_subclass = await get_table_as_list(conn, get_c_character_subclass(),
                                                                CharacterSubclass, CharacterSubclassSchema())
            self.c_character_race = await get_table_as_list(conn, get_c_character_race(), CharacterRace,
                                                            CharacterRaceSchema())
            self.c_character_subrace = await get_table_as_list(conn, get_c_character_subrace(), CharacterSubrace,
                                                               CharacterSubraceSchema())
            self.c_global_modifier = await get_table_as_list(conn, get_c_global_modifier(), GlobalModifier,
                                                             GlobalModifierSchema())
            self.c_host_status = await get_table_as_list(conn, get_c_host_status(), HostStatus,
                                                         HostStatusSchema())
            self.c_arena_tier = await get_table_as_list(conn, get_c_arena_tier(), ArenaTier, ArenaTierSchema())
            self.c_adventure_tier = await get_table_as_list(conn, get_c_adventure_tier(), AdventureTier,
                                                            AdventureTierSchema())
            self.c_adventure_rewards = await get_table_as_list(conn, get_c_adventure_rewards(), AdventureRewards,
                                                               AdventureRewardsSchema())
            self.c_shop_type = await get_table_as_list(conn, get_c_shop_type(), ShopType, ShopTypeSchema())
            self.c_activity = await get_table_as_list(conn, get_c_activity(), Activity, ActivitySchema())
            self.c_faction = await get_table_as_list(conn, get_c_faction(), Faction, FactionSchema())
            self.c_dashboard_type = await get_table_as_list(conn, get_c_dashboard_type(), DashboardType,
                                                            DashboardTypeSchema())
            self.c_level_caps = await get_table_as_list(conn, get_c_level_caps(), LevelCaps, LevelCapsSchema())

        end = timer()
        print(f'Time to reload Compendium [ {end - start} ]')

    def get_object(self, node: str, value: str | int = None):
        if not hasattr(self, node):
            return None
        elif isinstance(value, int):
            return next((s for s in self.__getattribute__(node) if s.id == value), None)
        elif value is not None:
            return next((s for s in self.__getattribute__(node) if s.value.upper() == value.upper()), None)
        else:
            return None
