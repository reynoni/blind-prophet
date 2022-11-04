from typing import List

import discord
from discord import CategoryChannel


async def character_class_autocomplete(ctx: discord.AutocompleteContext):
    return [c.value for c in ctx.bot.compendium.c_character_class if c.value.lower().startswith(ctx.value.lower())]


async def character_race_autocomplete(ctx: discord.AutocompleteContext):
    return [r.value for r in ctx.bot.compendium.c_character_race if r.value.lower().startswith(ctx.value.lower())]


async def character_subclass_autocomplete(ctx: discord.AutocompleteContext):
    picked_class = ctx.options["character_class"]
    if picked_class is None:
        return None
    char_class = ctx.bot.compendium.get_object("c_character_class", picked_class)
    return [s.value for s in ctx.bot.compendium.c_character_subclass if s.parent == char_class.id
            and (s.value.lower().startswith(ctx.value.lower())
                 or ctx.value.lower() in s.value.lower())]


async def character_subrace_autocomplete(ctx: discord.AutocompleteContext):
    picked_race = ctx.options["character_race"]
    if picked_race is None:
        return None
    char_race = ctx.bot.compendium.get_object("c_character_race", picked_race)

    return [s.value for s in ctx.bot.compendium.c_character_subrace if s.parent == char_race.id
            and (s.value.lower().startswith(ctx.value.lower())
                 or ctx.value.lower() in s.value.lower())]


async def faction_autocomplete(ctx: discord.AutocompleteContext):
    return [c.value for c in ctx.bot.compendium.c_faction if c.value.lower().startswith(ctx.value.lower())
            or ctx.value.lower() in c.value.lower()]
