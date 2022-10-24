from ProphetBot.models.db import *
from sqlalchemy.sql.selectable import FromClause

from ProphetBot.models.db_objects import BP_Guild


def get_guild(guild_id: int) -> FromClause:
    return guilds_table.select().where(
        guilds_table.c.id == guild_id
    )


def insert_new_guild(guild: BP_Guild):
    return guilds_table.insert().values(
        id=guild.id,
        max_level=guild.max_level,
        server_xp=guild.server_xp,
        weeks=guild.weeks,
        max_reroll=guild.max_reroll,
        mod_roles=guild.mod_roles,
        lore_roles=guild.lore_roles
    )


def update_guild_settings(guild: BP_Guild):
    return guilds_table.update() \
        .where(guilds_table.c.id == guild.id) \
        .values(
        max_level=guild.max_level,
        server_xp=guild.server_xp,
        weeks=guild.weeks,
        max_reroll=guild.max_reroll,
        mod_roles=guild.mod_roles,
        lore_roles=guild.lore_roles
    )
