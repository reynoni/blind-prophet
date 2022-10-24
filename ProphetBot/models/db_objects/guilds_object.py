from typing import List

import discord.utils
from discord import ApplicationContext


class BP_Guild(object):
    id: int
    max_level: int
    server_xp: int
    weeks: int
    max_reroll: int
    mod_roles: List[int]
    lore_roles: List[int]

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_mod_role_names(self, ctx: ApplicationContext):
        names = []
        for r in self.mod_roles:
            names.append(ctx.guild.get_role(r).name)

        if len(names) == 0:
            names.append("None")
        return names

    def get_loremaster_role_names(self, ctx: ApplicationContext):
        names = []
        for r in self.lore_roles:
            names.append(ctx.guild.get_role(r).name)

        if len(names) == 0:
            names.append("None")
        return names
