from datetime import datetime
from typing import List

from ProphetBot.models.db import *
from sqlalchemy import null, and_, or_
from sqlalchemy.sql.selectable import FromClause, TableClause


def select_active_arena_by_channel(channel_id: int) -> FromClause:
    return arenas_table.select().where(
        and_(arenas_table.c.channel_id == channel_id, arenas_table.c.end_ts == null())
    )


def insert_new_arena(channel_id: int, msg_id: int, role_id: int, host_id: int) -> TableClause:
    return arenas_table.insert().values(
        channel_id=channel_id,
        pin_message_id=msg_id,
        role_id=role_id,
        host_id=host_id
    )


def update_arena_tier(arena_id: int, new_tier: int):
    return arenas_table.update() \
        .where(arenas_table.c.id == arena_id) \
        .values(tier=new_tier)


def update_arena_completed_phases(arena_id: int, new_phases: int):
    return arenas_table.update() \
        .where(arenas_table.c.id == arena_id) \
        .values(completed_phases=new_phases)


def close_arena_by_id(arena_id: int):
    return arenas_table.update() \
        .where(arenas_table.c.id == arena_id) \
        .values(end_ts=datetime.utcnow())


def get_dashboard_by_categorychannl_id(categorychannel_id: int) -> FromClause:
    return category_dashboards_table.select().where(
        category_dashboards_table.c.categorychannel_id == categorychannel_id
    )


def get_all_dashboards() -> FromClause:
    return category_dashboards_table.select()


def insert_new_dashboard(category_id: int, post_channel_id: int, post_id: int, excluded_channels: List[int]):
    return category_dashboards_table.insert().values(
        categorychannel_id=category_id,
        dashboard_post_channel_id=post_channel_id,
        dashboard_post_id=post_id,
        excluded_channel_ids=excluded_channels
    )


def insert_new_global_event(guild_id: int, name: str, base_gold: int, base_exp: int, base_mod: str, combat: bool):
    return ref_gb_staging_table.insert().values(
        guild_id=guild_id,
        name=name,
        base_gold=base_gold,
        base_exp=base_exp,
        base_mod=base_mod,
        combat=combat
    )


def get_active_global(guild_id: int) -> FromClause:
    return ref_gb_staging_table.select().where(
        and_(ref_gb_staging_table.c.guild_id == guild_id, ref_gb_staging_table.c.active == True)
    )


def update_global_event(event_id: int, name: str, base_gold: int, base_exp: int, base_mod: str, combat: bool):
    return ref_gb_staging_table.update() \
        .where(ref_gb_staging_table.c.id == event_id) \
        .values(name=name, base_gold=base_gold, base_exp=base_exp, base_mod=base_mod, combat=combat)


def close_global_event(event_id: int):
    return ref_gb_staging_table.update() \
        .where(ref_gb_staging_table.c.id == event_id) \
        .values(active=False)


def update_global_channels(event_id: int, channels: List[int]):
    return ref_gb_staging_table.update() \
        .where(ref_gb_staging_table.c.id == event_id) \
        .values(channels=channels)


def get_all_global_players(event_id: int) -> FromClause:
    return ref_gb_staging_player_table.select().where(
        ref_gb_staging_player_table.c.global_id == event_id
    )


def add_global_player(event_id: int, player_id: int, modifier: str, host: str, gold: int, exp: int, update: bool,
                      active: bool):
    return ref_gb_staging_player_table.insert().values(
        global_id=event_id,
        player_id=player_id,
        modifier=modifier,
        host=host,
        gold=gold,
        exp=exp,
        update=update,
        active=active
    )


def update_global_player(id: int, modifier: str, host: str, gold: int, exp: int, update: bool, active: bool):
    return ref_gb_staging_player_table.update() \
        .where(ref_gb_staging_player_table.c.id == id) \
        .values(modifier=modifier,
                host=host,
                gold=gold,
                exp=exp,
                update=update,
                active=active)
