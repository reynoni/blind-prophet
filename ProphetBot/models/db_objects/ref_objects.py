from typing import List

import discord.utils
from discord import ApplicationContext, Role, TextChannel, CategoryChannel, Message, Bot

from ProphetBot.models.db_objects import DashboardType


class RefCategoryDashboard(object):
    category_channel_id: int
    dashboard_post_channel_id: int
    dashboard_post_id: int
    excluded_channel_ids: List[int]
    dashboard_type: int

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def channels_to_check(self, bot: Bot) -> List[TextChannel]:
        category: CategoryChannel = bot.get_channel(self.category_channel_id)
        if category is not None:
            return list(filter(lambda c: c.id not in self.excluded_channel_ids, category.text_channels))
        else:
            return []

    def get_category_channel(self, bot: Bot) -> CategoryChannel | None:
        return bot.get_channel(self.category_channel_id)

    async def get_pinned_post(self, bot: Bot) -> Message | None:
        channel = bot.get_channel(self.dashboard_post_channel_id)
        if channel is not None:
            try:
                msg = await channel.fetch_message(self.dashboard_post_id)
            except discord.errors.NotFound as e:
                return None
            return msg
        return None


class RefWeeklyStipend(object):
    role_id: int
    ratio: float
    reason: str

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_role(self, ctx: ApplicationContext | discord.Interaction) -> Role:
        return discord.utils.get(ctx.guild.roles, id=self.role_id)
