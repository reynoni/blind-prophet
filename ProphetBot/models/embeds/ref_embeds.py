from typing import Dict, List

import discord
from discord import Embed, Color, ApplicationContext

from ProphetBot.constants import MAX_PHASES, THUMBNAIL
from ProphetBot.models.db_objects import GlobalEvent, GlobalPlayer
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


# TODO: Loop through compendium c_global_modifiers and c_host_status to find players that way, so we aren't hard-coding modifiers here
# TODO: Show message_count
class GlobalEmbed(Embed):
    def __init__(self, ctx: ApplicationContext, g_event: GlobalEvent, players: List[GlobalPlayer],
                 gblist: bool = False):
        super().__init__(title=f"Global - Log Preview",
                         colour=Color.random())

        names = g_event.get_channel_names(ctx.bot)
        active_players = []
        h_players = []
        m_players = []
        l_players = []
        o_players = []
        host_players = []

        self.set_thumbnail(
            url=THUMBNAIL
        )

        if g_event.combat:
            for p in players:
                if p.active:
                    active_players.append(p)
                if not p.update:  # TODO: Need to check if players are active for this
                    o_players.append(p)
                if p.host:
                    host_players.append(p)

            self.add_field(name=f"**Information for combat global {g_event.name}**",
                           value=f"\n *Base gold:* {g_event.base_gold} \n *Base xp:* {g_event.base_xp} \n *# "
                                 f"Players:* {len(active_players)}",
                           inline=False)
        else:
            for p in players:
                if p.active:
                    active_players.append(p)
                if p.modifier.id != g_event.base_mod.id and p.host.value != "Hosting Only":
                    if p.modifier.value == "High":
                        h_players.append(p)
                    if p.modifier.value == "Medium":
                        m_players.append(p)
                    if p.modifier.value == "Low":
                        l_players.append(p)
                if not p.update:
                    o_players.append(p)
                if p.host:
                    host_players.append(p)

            self.add_field(name=f"**Information for {g_event.name}**",
                           value=f"\n *Base gold:* {g_event.base_gold} \n *Base xp:* {g_event.base_xp} \n *Base "
                                 f"mod:* {g_event.base_mod.value} \n *# Players:* {len(active_players)}",
                           inline=False)

        if names:
            self.add_field(name="**Scraped Channels**",
                           value="\n".join([f"\u200b # {c}" for c in names]),
                           inline=False)
        else:
            self.add_field(name="**Scraped Channels**",
                           value="None",
                           inline=False)

        if h_players:
            self.add_field(name="**High Effort Overrides**",
                           value="\n".join([f"\u200b {p.get_name(ctx)}" for p in h_players]),
                           inline=False)

        if m_players:
            self.add_field(name="**Medium Effort Overrides**",
                           value="\n".join([f"\u200b {p.get_name(ctx)}" for p in m_players]),
                           inline=False)

        if l_players:
            self.add_field(name="**Low Effort Overrides**",
                           value="\n".join([f"\u200b {p.get_name(ctx)}" for p in l_players]),
                           inline=False)

        if o_players:
            self.add_field(name="**Manual Overrides (gold, xp)**",
                           value="\n".join([f"\u200b {p.get_name(ctx)} ({p.gold}, {p.xp})" for p in o_players]),
                           inline=False)
        if host_players:
            self.add_field(name="**Hosts**",
                           value="\n".join([f"\u200b {p.get_name(ctx)} - {p.host.value}" for p in host_players]),
                           inline=False)

        if gblist:
            self.add_field(name="**All active players (gold, xp)**",
                           value="\n".join(f"\u200b {p.get_name(ctx)} ({p.gold}, {p.xp})" for p in active_players))
