import sqlalchemy as sa
from sqlalchemy import MetaData, Column, BigInteger, Integer

metadata = MetaData()

# TODO: This should be replaced with ref_gategory_dashboard_table
category_dashboards_table = sa.Table(
    "category_dashboards",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement='auto'),
    Column("categorychannel_id", BigInteger, nullable=False),
    Column("dashboard_post_channel_id", BigInteger, nullable=False),
    Column("dashboard_post_id", BigInteger, nullable=False),
    Column("excluded_channel_ids", sa.ARRAY(BigInteger), nullable=False)
)