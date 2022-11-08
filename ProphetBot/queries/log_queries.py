from datetime import datetime, timedelta

from sqlalchemy import and_
from sqlalchemy.sql import FromClause

from ProphetBot.models.db_objects import DBLog
from ProphetBot.models.db_tables import log_table


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


def get_two_weeks_logs(char_id: int) -> FromClause:
    two_weeks_ago = datetime.today() - timedelta(days=14)
    return log_table.select().where(
        and_(log_table.c.character_id == char_id, log_table.c.created_ts > two_weeks_ago)
    ).order_by(log_table.c.id.desc())


def get_log_by_player_and_activity(char_id: int, act_id: int) -> FromClause:
    return log_table.select().where(
        and_(log_table.c.character_id == char_id, log_table.c.activity == act_id)
    )
