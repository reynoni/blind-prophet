import aiopg.sa
import discord
from discord import ApplicationContext, TextChannel, Role

from ProphetBot.models.db_objects import RefCategoryDashboard, RefWeeklyStipend
from ProphetBot.models.schemas import RefCategoryDashboardSchema, RefWeeklyStipendSchema
from ProphetBot.queries import get_dashboard_by_category_channel, get_weekly_stipend_query


async def get_dashboard_from_category_channel_id(ctx: ApplicationContext) -> RefCategoryDashboard | None:
    category_channel_id = ctx.channel.category_id

    if category_channel_id is None:
        return None

    async with ctx.bot.db.acquire() as conn:
        results = await conn.execute(get_dashboard_by_category_channel(category_channel_id))
        row = await results.first()

    if row is None:
        return None
    else:
        dashboard: RefCategoryDashboard = RefCategoryDashboardSchema().load(row)
        return dashboard


async def get_last_message(channel: TextChannel) -> discord.Message | None:
    last_message = channel.last_message
    if last_message is None:
        try:
            lm_id = channel.last_message_id
            last_message = await channel.fetch_message(lm_id) if lm_id is not None else None
        except discord.errors.HTTPException as e:
            print(f"Skipping channel {channel.name}: [ {e} ]")
            return None
    return last_message


async def get_weekly_stipend(db: aiopg.sa.Engine, role: Role) -> RefWeeklyStipend | None:
    async with db.acquire() as conn:
        results = await conn.execute(get_weekly_stipend_query(role.id))
        row = await results.first()

    if row is None:
        return None
    else:
        stipend: RefWeeklyStipend = RefWeeklyStipendSchema().load(row)
        return stipend
