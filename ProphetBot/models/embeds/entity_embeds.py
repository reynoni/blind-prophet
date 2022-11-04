import calendar
from typing import List

import discord
from discord import Embed, Member, ApplicationContext, Color

from ProphetBot.constants import THUMBNAIL
from ProphetBot.models.db_objects import PlayerCharacter, PlayerCharacterClass, DBLog, LevelCaps, Arena, Adventure


class NewCharacterEmbed(Embed):
    def __init__(self, character: PlayerCharacter, player: Member, char_class: PlayerCharacterClass,
                 log: DBLog, ctx: ApplicationContext):
        super().__init__(title=f"Character Created - {character.name}",
                         description=f"**Player:** {player.mention}\n"
                                     f"**Race:** {character.get_formatted_race()}\n"
                                     f"**Class:** {char_class.get_formatted_class()}\n"
                                     f"**Starting Gold:** {character.gold}\n"
                                     f"**Starting Level:** {character.get_level()}\n",
                         color=discord.Color.random())
        self.set_thumbnail(url=player.display_avatar.url)
        self.set_footer(text=f"Created by: {ctx.author} - Log #: {log.id}",
                        icon_url=ctx.author.display_avatar.url)


class CharacterGetEmbed(Embed):
    def __init__(self, character: PlayerCharacter, char_class: List[PlayerCharacterClass],
                 cap: LevelCaps, ctx: ApplicationContext):
        super().__init__(title=f"Character Info - {character.name}")

        self.description = f"**Class**:"
        self.description += f"\n".join([f" {c.get_formatted_class()}" for c in char_class])
        self.description += f"\n**Faction:** {character.faction.value}\n" \
                            f"**Level:** {character.get_level()}\n" \
                            f"**Experience:** {character.xp}\n" \
                            f"**Wealth:** {character.gold} gp\n"

        faction_role = character.faction.get_faction_role(ctx)
        self.color = faction_role.color if faction_role else Color.dark_grey()
        self.set_thumbnail(url=character.get_member(ctx).display_avatar.url)

        self.add_field(name="Weekly Limits: ",
                       value=f"\u200b \u200b \u200b Diversion GP: {character.div_gold}/{cap.max_gold}\n"
                             f"\u200b \u200b \u200b Diversion XP: {character.div_xp}/{cap.max_xp}",
                       inline=False)

        if character.get_level() < 3:
            self.add_field(name="First Steps Quests:",
                           value=f"\u200b \u200b \u200b Level {character.get_level()} RPs: "
                                 f"{character.completed_rps}/{character.needed_rps}\n"
                                 f"\u200b \u200b \u200b Level {character.get_level()} Arenas: "
                                 f"{character.completed_arenas}/{character.needed_arenas}")


class HxLogEmbed(Embed):
    def __init__(self, log_ary: [DBLog], character: PlayerCharacter, ctx: ApplicationContext):
        super().__init__(title=f"Character Logs - {character.name}",
                         colour=discord.Colour.random())

        self.set_thumbnail(url=character.get_member(ctx).display_avatar.url)

        if len(log_ary) < 1:
            self.description(f"No logs for this week")

        for log in log_ary:
            log_time = log.created_ts
            unix_timestamp = calendar.timegm(log_time.utctimetuple())

            value = f"**Author:** {log.get_author(ctx).mention}\n" \
                    f"**Activity:** {log.activity.value}\n" \
                    f"**Gold:** {log.gold}\n" \
                    f"**XP:** {log.xp}\n"

            if log.notes is not None:
                value += f"**Notes:** {log.notes}"

            self.add_field(name=f"Log # {log.id} - <t:{unix_timestamp}>", value=value, inline=False)


class DBLogEmbed(Embed):
    def __init__(self, ctx: ApplicationContext, log_entry: DBLog, character: PlayerCharacter):
        super().__init__(title=f"{log_entry.activity.value} Logged - {character.name}",
                         color=Color.random())

        player = character.get_member(ctx)
        description = f"**Player:** {player.mention}\n"
        if log_entry.gold is not None:
            description += f"**Gold:** {log_entry.gold}\n"
        if log_entry.xp is not None:
            description += f"**Experience:** {log_entry.xp}\n"
        if hasattr(log_entry, "note"):
            description += f"**Notes:** {log_entry.notes}\n"

        self.description = description
        self.set_thumbnail(url=player.display_avatar.url)
        self.set_footer(text=f"Logged by {ctx.author} - ID: {log_entry.id}",
                        icon_url=ctx.author.display_avatar.url)  # TODO: Something wrong here


class ArenaPhaseEmbed(Embed):
    def __init__(self, ctx: ApplicationContext, arena: Arena, result: str):
        rewards = f"{arena.get_host(ctx).mention}: 'HOST'\n"
        bonus = (arena.completed_phases > arena.tier.max_phases / 2) and result == 'WIN'
        arena_role = arena.get_role(ctx)
        players = list(set(filter(lambda p: p.id != arena.host_id, arena_role.members)))

        for player in players:
            rewards += f"{player.mention}: '{result}'"
            rewards += ', `BONUS`\n' if bonus else '\n'

        super().__init__(
            title=f"Phase {arena.completed_phases} Complete!",
            description=f"Complete phases: **{arena.completed_phases} / {arena.tier.max_phases}**",
            color=discord.Color.random()
        )

        self.set_thumbnail(url=THUMBNAIL)

        self.add_field(name="The following rewards have been applied:", value=rewards, inline=False)


class ArenaStatusEmbed(Embed):
    def __init__(self, ctx: ApplicationContext | discord.Interaction, arena: Arena):
        super().__init__(title=f"Arena Status",
                         description=f"**Tier** {arena.tier.id}\n"
                                     f"**Completed Phases:** {arena.completed_phases} / {arena.tier.max_phases}",
                         color=Color.random())

        self.set_thumbnail(url=THUMBNAIL)

        if arena.completed_phases == 0:
            self.description += "\n\nUse the button below to join!"
        elif arena.completed_phases >= arena.tier.max_phases / 2:
            self.description += "\nBonus active!"

        self.add_field(name="**Host:**", value=f"\u200b - {arena.get_host(ctx).mention}",
                       inline=False)

        players = list(set(filter(lambda p: p.id != arena.host_id,
                                  arena.get_role(ctx).members)))

        if len(players) > 0:
            self.add_field(name="**Players:**",
                           value="\n".join([f"\u200b -{p.mention}" for p in players]),
                           inline=False)


class AdventureEPEmbed(Embed):
    def __init__(self, ctx: ApplicationContext, adventure: Adventure, ep: int):
        super().__init__(
            title="Adventure Rewards",
            description=f"**Adventure:** {adventure.name}\n"
                        f"**EP Earned:** {ep}\n"
                        f"**EP Earned to date:** {adventure.ep}\n"
                        f"*Note: Rewards are 1/2 of your diversion caps for each EP*\n",
            color=Color.random()
        )

        self.add_field(
            name="DM(s)",
            value="\n".join([f"\u200b - {p.mention}" for p in list(set(filter(lambda p: p.id in adventure.dms,
                                                                              adventure.get_adventure_role(
                                                                                  ctx).members)))]),
            inline=False
        )

        self.add_field(
            name="Players",
            value="\n".join([f"\u200b - {p.mention}" for p in list(set(filter(lambda p: p.id not in adventure.dms,
                                                                              adventure.get_adventure_role(ctx).members)))]),
            inline=False
        )

        self.set_thumbnail(url=THUMBNAIL)
        self.set_footer(text=f"Logged by {ctx.author.name}#{ctx.author.discriminator}",
                        icon_url=ctx.author.display_avatar.url)
