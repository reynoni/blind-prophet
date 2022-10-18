from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Column, Integer, BigInteger, String, BOOLEAN, DateTime, null
from ProphetBot.models.db.base import metadata

arenas_table = sa.Table(
    "arenas",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("channel_id", BigInteger, nullable=False),
    Column("pin_message_id", BigInteger, nullable=False),
    Column("role_id", BigInteger, nullable=False),
    Column("host_id", Integer, nullable=False),
    Column("tier", Integer, nullable=False, default=1),  # ref: > c_arena_tier.id
    Column("completed_phases", Integer, nullable=False, default=0),
    Column("created_ts", DateTime, nullable=False, default=datetime.utcnow()),
    Column("end_ts", DateTime, nullable=True, default=null())
)

guilds_table = sa.Table(
    "guilds",
    metadata,
    Column("id", BigInteger, primary_key=True, nullable=False),
    Column("max_level", Integer, nullable=False, default=1),
    Column("server_xp", Integer, nullable=False, default=0),
    Column("weeks", Integer, nullable=False, default=0),
    Column("mod_roles", sa.ARRAY(BigInteger), nullable=True, default=[]),
    Column("lore_roles", sa.ARRAY(BigInteger), nullable=True, default=[])
)

players_table = sa.Table(
    "players",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("discord_id", BigInteger, nullable=False),
    Column("guild_id", BigInteger, nullable=False),  # ref: > guilds.id
    Column("created_ts", DateTime, nullable=False, default=datetime.utcnow()),
    Column("rerolls", Integer, nullable=False, default=0)
)

characters_table = sa.Table(
    "characters",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("name", String, nullable=False),
    Column("race", Integer, nullable=False),  # ref: > c_character_race.id
    Column("subrace", Integer, nullable=False),  # ref: > c_character_subrace_id
    Column("xp", Integer, nullable=False, default=0),
    Column("gold", Integer, nullable=False,default=0),
    Column("player_id", Integer, nullable=False),  # ref: > players.id
    Column("faction", sa.ARRAY(Integer), nullable=True, default=[]),  # ref: <> c_faction.id
    Column("action", BOOLEAN, nullable=False, default=True)
)

character_class_table = sa.Table(
    "character_class",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("character", Integer, nullable=False),  # ref: > characters.id
    Column("class", Integer, nullable=False),  # ref: > c_character_class.id
    Column("subclass", Integer, nullable=True),  # ref: > c_character_subclass.id
    Column("level", Integer, nullable=False, default=1),
    Column("primary", BOOLEAN, nullable=True)
)

shops_table = sa.Table(
    "shops",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("name", String, nullable=False),
    Column("type", Integer, nullable=False),  # ref: > c_shop_type.id
    Column("owner", Integer, nullable=False),  # ref: > players.id
    Column("rarity", Integer, nullable=False),  # ref: > c_rarity.id
    Column("prestige", Integer, nullable=True),
    Column("shelf", Integer, nullable=True, default=0),
    Column("network", Integer, nullable=True, default=0),
    Column("mastery", Integer, nullable=True, default=0),
    Column("seeks_remaining", Integer, nullable=True, default=0),
    Column("active", BOOLEAN, nullable=False, default=True)
)

log_table = sa.Table(
    "log",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("author", BigInteger, nullable=False),
    Column("xp", Integer, nullable=True),
    Column("gold", Integer, nullable=True),
    Column("created_ts", DateTime, nullable=False, default=datetime.utcnow()),
    Column("char_id", Integer, nullable=False),  # ref: > characters.id
    Column("activity", Integer, nullable=False),  # ref: > c_activity.id
    Column("notes", String, nullable=True),
    Column("shop_id", Integer, nullable=True),  # ref: > shops.id
    Column("adventure_id", Integer, nullable=True)  # ref: > adventures.id
)

adventures_table = sa.Table(
    "adventures",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("name", String, nullable=False),
    Column("role_id", BigInteger, nullable=False),
    Column("dms", sa.ARRAY(Integer), nullable=False),  # ref: <> players.id
    Column("tier", Integer, nullable=False),  # ref: > c_adventure_tier.id
    Column("category_channel_id", BigInteger, nullable=False),
    Column("created_ts", DateTime, nullable=False, default=datetime.utcnow()),
    Column("end_ts", DateTime, nullable=True),
    Column("active", BOOLEAN, nullable=False, default=True)
)

item_blacksmith_table = sa.Table(
    "item_blacksmith",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("name", String, nullable=False),
    Column("sub_type", Integer, nullable=False),  # ref: > c_blacksmith_type.id
    Column("rarity", Integer, nullable=False),  # ref: > c_rarity.id
    Column("cost", Integer, nullable=False),
    Column("item_modifier", BOOLEAN, nullable=False, default=False),
    Column("attunement", BOOLEAN, nullable=False, default=False),
    Column("seeking_only", BOOLEAN, nullable=False, default=False),
    Column("source", String, nullable=True),
    Column("notes", String, nullable=True)
)

item_wondrous_table = sa.Table(
    "item_wondrous",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("name", String, nullable=False),
    Column("rarity", Integer, nullable=False),  # ref: > c_rarity.id
    Column("cost", Integer, nullable=False),
    Column("attunement", BOOLEAN, nullable=False, default=False),
    Column("seeking_only", BOOLEAN, nullable=False, default=False),
    Column("source", String, nullable=True),
    Column("notes", String, nullable=True)
)

item_consumable_table = sa.Table(
    "item_consumable",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("name", String, nullable=False),
    Column("sub_type", Integer, nullable=False),  # ref: > c_consumable_type.id
    Column("rarity", Integer, nullable=False),  # ref: > c_rarity.id
    Column("cost", Integer, nullable=False),
    Column("attunement", BOOLEAN, nullable=False, default=False),
    Column("seeking_only", BOOLEAN, nullable=False, default=False),
    Column("source", String, nullable=True),
    Column("notes", String, nullable=True)
)

item_scrolls_table = sa.Table(
    "item_scrolls",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("name", String, nullable=False),
    Column("rarity", Integer, nullable=False),  # ref: > c_rarity.id
    Column("cost", Integer, nullable=False),
    Column("level", Integer, nullable=False),
    Column("school", Integer, nullable=False),  # ref: > c_magic_school.id
    Column("classes", sa.ARRAY(Integer), nullable=False),  # ref: > c_character_class.id
    Column("source", String, nullable=True),
    Column("notes", String, nullable=True)
)