from typing import Dict, Any

from discord import Embed, Color

from ProphetBot.constants import THUMBNAIL
from ProphetBot.models.db_objects import *
from ProphetBot.models.db_objects import PlayerGuild
from ProphetBot.models.sheets_objects import LogEntry, Character, Adventure


def linebreak() -> Dict[str, Any]:
    return {
        'name': discord.utils.escape_markdown('___________________________________________'),
        'value': '\u200B',
        'inline': False
    }


class LogEmbed(Embed):
    def __init__(self, ctx: ApplicationContext, log_entry: LogEntry):
        player = log_entry.character.get_member(ctx)
        description = f"**Player:** {player.mention}\n"
        if log_entry.outcome:
            description += f"**Item/Reason:** {log_entry.outcome}\n"
        if log_entry.gp is not None:
            description += f"**Gold:** {log_entry.gp}\n"
        if log_entry.xp is not None:
            description += f"**Experience:** {log_entry.xp}"

        super().__init__(
            title=f"{log_entry.activity.value} Logged - {log_entry.character.name}",
            description=description,
            color=Color.random()
        )
        self.set_thumbnail(url=player.display_avatar.url)
        self.set_footer(text=f"Logged by {log_entry.author}", icon_url=ctx.author.display_avatar.url)


class AdventureRewardEmbed(Embed):
    def __init__(self, ctx: ApplicationContext, dms: List[Character], players: List[Character],
                 adventure: Adventure, ep: int):
        super().__init__(
            title="Adventure Rewards",
            description=f"**Adventure**: {adventure.name}\n"
                        f"**EP Earned**: {ep}\n"
                        f"*Note: Rewards are 1/2 of your diversion caps for each EP*\n",
            color=Color.random()
        )
        self.add_field(
            name="DM(s)",
            value="\n".join([f"\u200b -{m.mention()}" for m in dms]),
            inline=False
        )
        self.add_field(
            name="Players",
            value="\n".join([f"\u200b -{m.mention()}" for m in players]),
            inline=False
        )
        self.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/794989941690990602/972998353103233124/IMG_2177.jpg"
        )
        author = f"{ctx.author.name}#{ctx.author.discriminator}"
        self.set_footer(text=f"Logged by {author}", icon_url=ctx.author.display_avatar.url)


class ErrorEmbed(Embed):

    def __init__(self, *args, **kwargs):
        kwargs['title'] = "Error:"
        kwargs['color'] = Color.brand_red()
        super().__init__(**kwargs)


class GlobalEmbed(Embed):
    def __init__(self, ctx: ApplicationContext, globEvent: gEvent, players: List[gPlayer], gblist: bool = False):
        super().__init__(title=f"Global - Log Preview",
                         colour=Color.random())

        names = globEvent.get_channel_names(ctx=ctx)
        aPlayers = []
        hPlayers = []
        mPlayers = []
        lPlayers = []
        oPlayers = []
        hostPlayers = []

        self.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/794989941690990602/972998353103233124/IMG_2177.jpg"
        )

        if globEvent.combat:
            for p in players:
                if p.active:
                    aPlayers.append(p)
                if not p.update:
                    oPlayers.append(p)
                if p.host:
                    hostPlayers.append(p)

            self.add_field(name=f"**Information for combat global {globEvent.name}**",
                           value=f"\n *Base gold:* {globEvent.base_gold} \n *Base exp:* {globEvent.base_exp} \n *# "
                                 f"Players:* {len(aPlayers)}",
                           inline=False)
        else:
            for p in players:
                if p.active:
                    aPlayers.append(p)
                if p.modifier != globEvent.base_mod and p.host != "Hosting Only":
                    if p.modifier == "High":
                        hPlayers.append(p)
                    if p.modifier == "Medium":
                        mPlayers.append(p)
                    if p.modifier == "Low":
                        lPlayers.append(p)
                if not p.update:
                    oPlayers.append(p)
                if p.host:
                    hostPlayers.append(p)

            self.add_field(name=f"**Information for {globEvent.name}**",
                           value=f"\n *Base gold:* {globEvent.base_gold} \n *Base exp:* {globEvent.base_exp} \n *Base "
                                 f"mod:* {globEvent.base_mod} \n *# Players:* {len(aPlayers)}",
                           inline=False)

        if names:
            self.add_field(name="**Scraped Channels**",
                           value="\n".join([f"\u200b # {c}" for c in names]),
                           inline=False)
        else:
            self.add_field(name="**Scraped Channels**",
                           value="None",
                           inline=False)

        if hPlayers:
            self.add_field(name="**High Effort Overrides**",
                           value="\n".join([f"\u200b {p.get_name(ctx)}" for p in hPlayers]),
                           inline=False)

        if mPlayers:
            self.add_field(name="**Medium Effort Overrides**",
                           value="\n".join([f"\u200b {p.get_name(ctx)}" for p in mPlayers]),
                           inline=False)

        if lPlayers:
            self.add_field(name="**Low Effort Overrides**",
                           value="\n".join([f"\u200b {p.get_name(ctx)}" for p in lPlayers]),
                           inline=False)

        if oPlayers:
            self.add_field(name="**Manual Overrides (gold, exp)**",
                           value="\n".join([f"\u200b {p.get_name(ctx)} ({p.gold}, {p.exp})" for p in oPlayers]),
                           inline=False)
        if hostPlayers:
            self.add_field(name="**Hosts**",
                           value="\n".join([f"\u200b {p.get_name(ctx)} - {p.host}" for p in hostPlayers]),
                           inline=False)

        if gblist:
            self.add_field(name="**All active players (gold, exp)**",
                           value="\n".join(f"\u200b {p.get_name(ctx)} ({p.gold}, {p.exp})" for p in aPlayers))


class GuildEmbed(Embed):
    def __init__(self, ctx: ApplicationContext, g: PlayerGuild):
        super().__init__(title=f'Server Settings for {ctx.guild.name}',
                         colour=Color.random())
        self.set_thumbnail(url=THUMBNAIL)

        self.add_field(name="**Settings**",
                       value=f"**Max Level:** {g.max_level}\n"
                             f"**Max Rerolls:** {g.max_reroll}",
                       inline=False)


class GuildStatus(Embed):
    def __init__(self, ctx: ApplicationContext, g: PlayerGuild):
        super().__init__(title=f"Server Info - {ctx.guild.name}",
                         color=Color.random(),
                         description=f"**Max Level:** {g.max_level}\n"
                                     f"**Server XP:** {g.server_xp}\n"
                                     f"**Week XP:** {g.week_xp}\n"
                                     f"**# Weeks:** {g.weeks}")

        self.set_thumbnail(url=THUMBNAIL)
