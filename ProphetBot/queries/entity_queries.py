from sqlalchemy.sql.selectable import FromClause
from sqlalchemy import and_, null
from ProphetBot.models.db_tables import guilds_table, adventures_table, arenas_table
from ProphetBot.models.db_objects import PlayerGuild, Adventure, Arena


def get_guild(guild_id: int) -> FromClause:
    return guilds_table.select().where(
        guilds_table.c.id == guild_id
    )


def insert_new_guild(guild: PlayerGuild):
    return guilds_table.insert().values(
        id=guild.id,
        max_level=guild.max_level,
        server_xp=guild.server_xp,
        weeks=guild.weeks,
        max_reroll=guild.max_reroll,
    ).returning(guilds_table)


def update_guild(guild: PlayerGuild):
    return guilds_table.update() \
        .where(guilds_table.c.id == guild.id) \
        .values(
        max_level=guild.max_level,
        server_xp=guild.server_xp,
        weeks=guild.weeks,
        week_xp=guild.week_xp,
    )


def insert_new_adventure(adventure: Adventure):
    return adventures_table.insert().values(
        name=adventure.name,
        role_id=adventure.role_id,
        dms=adventure.dms,
        tier=adventure.tier.id,
        category_channel_id=adventure.category_channel_id,
        ep=adventure.ep,
        end_ts=None if not hasattr(adventure, "end_ts") else adventure.end_ts,
    )


def update_adventure(adventure: Adventure):
    return adventures_table.update() \
        .where(adventures_table.c.id == adventure.id) \
        .values(
        name=adventure.name,
        role_id=adventure.role_id,
        dms=adventure.dms,
        tier=adventure.tier.id,
        category_channel_id=adventure.category_channel_id,
        ep=adventure.ep,
        end_ts=None if not hasattr(adventure, "end_ts") else adventure.end_ts
    )


def get_adventure_by_category_channel_id(category_channel_id: int) -> FromClause:
    return adventures_table.select().where(
        adventures_table.c.category_channel_id == category_channel_id
    )


def get_adventure_by_role_id(role_id: int) -> FromClause:
    return adventures_table.select().where(
        adventures_table.c.role_id == role_id
    )


def insert_new_arena(arena: Arena):
    return arenas_table.insert().values(
        channel_id=arena.channel_id,
        pin_message_id=arena.pin_message_id,
        role_id=arena.role_id,
        host_id=arena.host_id,
        tier=arena.tier.id,
        completed_phases=arena.completed_phases
    )


def update_arena(arena: Arena):
    return arenas_table.update().values(
        channel_id=arena.channel_id,
        pin_message_id=arena.pin_message_id,
        role_id=arena.role_id,
        host_id=arena.host_id,
        tier=arena.tier.id,
        completed_phases=arena.completed_phases,
        end_ts=None if not hasattr(arena, "end_ts") else arena.end_ts
    )


def get_arena_by_channel(channel_id: int) -> FromClause:
    return arenas_table.select().where(
        and_(arenas_table.c.channel_id == channel_id, arenas_table.c.end_ts == null())
    )


def select_active_arena_by_channel(channel_id: int) -> FromClause:
    return arenas_table.select().where(
        and_(arenas_table.c.channel_id == channel_id, arenas_table.c.end_ts == null())
    )


