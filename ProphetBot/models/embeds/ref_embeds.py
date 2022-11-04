from typing import Dict, List

import discord
from discord import Embed, Color

from ProphetBot.constants import MAX_PHASES
from ProphetBot.models.sheets_objects import Character


class RpDashboardEmbed(Embed):

    def __init__(self, channel_statuses: Dict[str, List[str]], category_name: str):
        super(RpDashboardEmbed, self).__init__(
            color=Color.dark_grey(),
            title=f"Channel Statuses - {category_name}",
            timestamp=discord.utils.utcnow()
        )
        if len(channel_statuses["Magewright"]) > 0:
            self.add_field(
                name="<:pencil:989284061786808380> -- Awaiting Magewright",
                value="\n".join(channel_statuses["Magewright"]),
                inline=False
            )
        self.add_field(
            name="<:white_check_mark:983576747381518396> -- Available",
            value="\n".join(channel_statuses["Available"]) or "\u200B",
            inline=False
        )
        self.add_field(
            name="<:x:983576786447245312> -- Unavailable",
            value="\n".join(channel_statuses["In Use"]) or "\u200B",
            inline=False
        )
        self.set_footer(text="Last Updated")

