from typing import List

import discord.utils
from discord import ApplicationContext, Message, Bot
from discord import CategoryChannel, TextChannel


class RpDashboard(object):
    category_id: int
    post_channel_id: int
    post_id: int
    excluded_channels: List[int]

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_categorychannel(self, bot: Bot) -> CategoryChannel | None:
        return bot.get_channel(self.category_id)

    async def get_pinned_post(self, bot: Bot) -> Message | None:
        channel = bot.get_channel(self.post_channel_id)
        if channel is not None:
            return await channel.fetch_message(self.post_id)
        return None

    def channels_to_check(self, bot: Bot) -> List[TextChannel]:
        category: CategoryChannel = bot.get_channel(self.category_id)
        if category is not None:
            return list(filter(lambda c: c.id not in self.excluded_channels, category.text_channels))
        return []
