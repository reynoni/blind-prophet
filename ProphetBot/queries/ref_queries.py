from typing import List

from ProphetBot.models.db_tables import *
from sqlalchemy import null, and_, or_
from sqlalchemy.sql.selectable import FromClause, TableClause

from ProphetBot.models.db_objects import RefCategoryDashboard, RefWeeklyStipend


def get_dashboard_by_category_channel(category_channel_id: int) -> FromClause:
    return ref_category_dashboard_table.select().where(
        ref_category_dashboard_table.c.category_channel_id == category_channel_id
    )


def insert_new_dashboard(dashboard: RefCategoryDashboard) -> TableClause:
    return ref_category_dashboard_table.insert().values(
        category_channel_id=dashboard.category_channel_id,
        dashboard_post_channel_id=dashboard.dashboard_post_channel_id,
        dashboard_post_id=dashboard.dashboard_post_id,
        excluded_channel_ids=dashboard.excluded_channel_ids,
        dashboard_type=dashboard.dashboard_type
    )


def update_dashboard(dashboard: RefCategoryDashboard):
    return ref_category_dashboard_table.update() \
        .where(
        ref_category_dashboard_table.c.category_channel_id == dashboard.category_channel_id
    ) \
        .values(
        category_channel_id=dashboard.category_channel_id,
        dashboard_post_channel_id=dashboard.dashboard_post_channel_id,
        dashboard_post_id=dashboard.dashboard_post_id,
        excluded_channel_ids=dashboard.excluded_channel_ids,
        dashboard_type=dashboard.dashboard_type
    )


def get_dashboards() -> FromClause:
    return ref_category_dashboard_table.select()


def delete_dashboard(dashboard: RefCategoryDashboard) -> TableClause:
    return ref_category_dashboard_table.delete().where(
        ref_category_dashboard_table.c.category_channel_id == dashboard.category_channel_id
    )


def get_weekly_stipend_query(role_id: int) -> FromClause:
    return ref_weekly_stipend_table.select().where(
        ref_weekly_stipend_table.c.role_id == role_id
    )


def insert_weekly_stipend(stipend: RefWeeklyStipend) -> TableClause:
    return ref_weekly_stipend_table.insert().values(
        role_id=stipend.role_id,
        guild_id=stipend.guild_id,
        ratio=stipend.ratio,
        reason=stipend.reason
    )


def update_weekly_stipend(stipend: RefWeeklyStipend) -> TableClause:
    return ref_weekly_stipend_table.update().where(ref_weekly_stipend_table.c.role_id == stipend.role_id) \
        .values(
        role_id=stipend.role_id,
        guild_id=stipend.guild_id,
        ratio=stipend.ratio,
        reason=stipend.reason
    )


def get_guild_weekly_stipends(guild_id: int) -> FromClause:
    return ref_weekly_stipend_table.select() \
        .where(ref_weekly_stipend_table.c.guild_id == guild_id) \
        .order_by(ref_weekly_stipend_table.c.role_id.desc())


def delete_weekly_stipend(stipend: RefWeeklyStipend) -> TableClause:
    return ref_weekly_stipend_table.delete().where(ref_weekly_stipend_table.c.role_id == stipend.role_id)
