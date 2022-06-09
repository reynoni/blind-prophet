from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, null
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
