from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Column, Integer, BigInteger, DateTime, null, BOOLEAN, String
from sqlalchemy.orm import declarative_base

db = declarative_base()
metadata = sa.MetaData()

arenas_table = sa.Table(
    "arenas",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("channel_id", BigInteger, nullable=False),
    Column("pin_message_id", BigInteger, nullable=False),
    Column("role_id", BigInteger, nullable=False),
    Column("host_id", BigInteger, nullable=False),
    Column("tier", Integer, default=1, nullable=False),
    Column("completed_phases", Integer, default=0),
    Column("created_ts", DateTime, default=datetime.utcnow()),
    Column("end_ts", DateTime, default=null())
)

category_dashboards_table = sa.Table(
    "category_dashboards",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("categorychannel_id", BigInteger, nullable=False),
    Column("dashboard_post_channel_id", BigInteger, nullable=False),
    Column("dashboard_post_id", BigInteger, nullable=False),
    Column("excluded_channel_ids", sa.ARRAY(BigInteger), nullable=False)
)

global_staging_table = sa.Table(
    "gb_staging",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("guild_id", BigInteger, nullable=False),
    Column("name", String, nullable=False),
    Column("base_gold", Integer, nullable=False),
    Column("base_exp", Integer, nullable=False),
    Column("base_mod", String, nullable=False),
    Column("combat", BOOLEAN, nullable=False),
    Column("channels", sa.ARRAY(BigInteger), nullable=True, default=[]),
    Column("active", BOOLEAN, nullable=False, default=True)
)


global_players_table = sa.Table(
    "gb_staging_players",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("global_id", Integer, nullable=False),
    Column("player_id", BigInteger, nullable=False),
    Column("modifier", String, nullable=True),
    Column("host", String, nullable=True),
    Column("gold", Integer,nullable=False),
    Column("exp", Integer, nullable=False),
    Column("update", BOOLEAN, nullable=False, default=True),
    Column("active", BOOLEAN, nullable=False, default=True)
)