import sqlalchemy as sa
from sqlalchemy import Column, Integer, BigInteger, Numeric, String, BOOLEAN
from ProphetBot.models.db.base import metadata

ref_category_dashboard_table = sa.Table(
    "ref_category_dashboard",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("guild", BigInteger, nullable=False),  # ref: > guilds.id
    Column("category_channel_id", BigInteger, nullable=False),
    Column("dashboard_post_channel_id", BigInteger, nullable=False),
    Column("dashboard_post_id", BigInteger, nullable=False),
    Column("excluded_channel_ids", sa.ARRAY(BigInteger), nullable=True),
    Column("dashboard_type", Integer, nullable=False)  # ref: > c_dashboard_type.id
)

ref_weekly_stipend_table = sa.Table(
    "ref_weekly_stipend",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("guild_id", BigInteger, nullable=False),  # ref: > guilds.id
    Column("role_ids", sa.ARRAY(BigInteger), nullable=False),
    Column("ratio", Numeric(precision=5, scale=2), nullable=False)
)

ref_gb_staging_table = sa.Table(
    "ref_gb_staging",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("guild_id", BigInteger, nullable=False),  # ref: > guilds.id
    Column("name", String, nullable=False),
    Column("base_gold", Integer, nullable=False),
    Column("base_xp", Integer, nullable=False),
    Column("base_mod", Integer, nullable=False),  # ref: c_global_modifier.id
    Column("combat", BOOLEAN, nullable=False),
    Column("channels", sa.ARRAY(BigInteger), nullable=True, default=[]),
    Column("active", BOOLEAN, nullable=False, default=True)
)

ref_gb_staging_player_table = sa.Table(
    "ref_gb_staging_player",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("global_id", Integer, nullable=False),  # ref: > ref_gb_staging.id
    Column("player_id", Integer, nullable=False),  # ref: > characters.player_id
    Column("modifier", Integer, nullable=True),  # ref: > c_global_modifier.id
    Column("host", Integer, nullable=True),  # ref: > c_host_status.id
    Column("gold", Integer, nullable=False),
    Column("xp", Integer, nullable=False),
    Column("update", BOOLEAN, nullable=False, default=True),
    Column("active", BOOLEAN, nullable=False, default=True),
    Column("num_messages", Integer, nullable=True, default=0),
    Column("channels", sa.ARRAY(BigInteger), nullable=True, default=[])
)
