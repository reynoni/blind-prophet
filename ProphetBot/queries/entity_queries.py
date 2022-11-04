from sqlalchemy.sql import FromClause
from sqlalchemy.sql.selectable import FromClause
from sqlalchemy import and_, null
from ProphetBot.models.db_tables import characters_table, character_class_table, guilds_table, adventures_table, log_table, \
    arenas_table
from ProphetBot.models.db_objects import PlayerCharacter, PlayerCharacterClass, PlayerGuild, Adventure, DBLog, Arena


def get_active_character(player_id: int, guild_id: int) -> FromClause:
    return characters_table.select().where(
        and_(characters_table.c.player_id == player_id, characters_table.c.guild_id == guild_id,
             characters_table.c.active == True)
    )


def insert_new_character(character: PlayerCharacter):
    return characters_table.insert().values(
        name=character.name,
        race=character.race.id,
        subrace=None if not hasattr(character.subrace, "id") else character.subrace.id,
        xp=character.xp,
        div_xp=character.div_xp,
        gold=character.gold,
        div_gold=character.div_gold,
        player_id=character.player_id,
        guild_id=character.guild_id,
        faction=character.faction.id,
        reroll=character.reroll,
        active=character.active
    ).returning(characters_table)


def update_character(character: PlayerCharacter):
    return characters_table.update() \
        .where(characters_table.c.id == character.id) \
        .values(
        name=character.name,
        race=character.race.id,
        subrace=None if not hasattr(character.subrace, "id") else character.subrace.id,
        xp=character.xp,
        div_xp=character.div_xp,
        gold=character.gold,
        div_gold=character.div_gold,
        player_id=character.player_id,
        guild_id=character.guild_id,
        faction=character.faction.id,
        reroll=character.reroll,
        active=character.active
    )


def insert_new_class(char_class: PlayerCharacterClass):
    return character_class_table.insert().values(
        character_id=char_class.character_id,
        primary_class=char_class.primary_class.id,
        subclass=None if not hasattr(char_class.subclass, "id") else char_class.subclass.id,
    )


def get_character_class(char_id: int) -> FromClause:
    return character_class_table.select().where(
        character_class_table.c.character_id == char_id
    )


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
        active=adventure.active
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
        end_ts=None if not hasattr(adventure, "end_ts") else adventure.end_ts,
        active=adventure.active
    )


def get_adventure_by_category_channel_id(category_channel_id: int) -> FromClause:
    return adventures_table.select().where(
        adventures_table.c.category_channel_id == category_channel_id
    )


def get_adventure_by_role_id(role_id: int) -> FromClause:
    return adventures_table.select().where(
        adventures_table.c.role_id == role_id
    )


def insert_new_log(log: DBLog):
    return log_table.insert().values(
        author=log.author,
        xp=log.xp,
        gold=log.gold,
        character_id=log.character_id,
        activity=log.activity.id,
        notes=None if not hasattr(log, "notes") else log.notes,
        shop_id=None if not hasattr(log, "shop_id") else log.shop_id,
        adventure_id=None if not hasattr(log, "adventure_id") else log.adventure_id
    ).returning(log_table)


def get_n_player_logs(char_id: int, n: int) -> FromClause:
    return log_table.select().where(log_table.c.character_id == char_id).order_by(log_table.c.id.desc()).limit(n)


def get_log_by_player_and_activity(char_id: int, act_id: int) -> FromClause:
    return log_table.select().where(
        and_(log_table.c.character_id == char_id, log_table.c.activity == act_id)
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


def get_multiple_characters(players: list[int], guild_id: int) -> FromClause:
    return characters_table.select().where(
        and_(characters_table.c.player_id.in_(players), characters_table.c.active == True,
             characters_table.c.guild_id == guild_id)
    ).order_by(characters_table.c.id.desc())


def get_characters(guild_id: int) -> FromClause:
    return characters_table.select().where(
        and_(characters_table.c.active == True, characters_table.c.guild_id == guild_id)
    ).order_by(characters_table.c.id.desc())
