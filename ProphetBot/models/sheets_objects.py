import datetime
import enum
import math
from typing import Dict, Any, List

import discord
from discord import OptionChoice, Member
from discord.commands.context import ApplicationContext


class CommandOptionEnum(enum.Enum):

    @classmethod
    def optionchoice_list(cls) -> List[OptionChoice]:
        return list(map(lambda o: OptionChoice(o.value), cls))

    @classmethod
    def values_list(cls) -> List[str]:
        return list(map(lambda v: v.value, cls))


class CharacterClass(CommandOptionEnum):
    ARTIFICER = 'Artificer'
    BARBARIAN = 'Barbarian'
    BARD = 'Bard'
    CLERIC = 'Cleric'
    DRUID = 'Druid'
    FIGHTER = 'Fighter'
    MONK = 'Monk'
    PALADIN = 'Paladin'
    RANGER = 'Ranger'
    ROGUE = 'Rogue'
    SORCERER = 'Sorcerer'
    WARLOCK = 'Warlock'
    WIZARD = 'Wizard'


class Faction(CommandOptionEnum):
    INITIATE = 'Guild Initiate'
    GUILD_MEMBER = "Guild Member"
    COPPER_DRAGONS = 'Order of the Copper Dragon'
    SILENT_WHISPERS = 'Silent Whispers'
    SILVER_WOLVES = 'Silver Wolves'
    CRIMSON_BLADES = 'Crimson Blades'
    CLOVER_CONCLAVE = 'Clover Conclave'
    SUNSTONE_LOTUS = 'Sunstone Lotus'
    FALCON_EYES = 'The Falcon Eyes'
    AZURE_GUARD = 'The Azure Guard'


class Activity(enum.Enum):
    arena = "ARENA"
    bonus = "BONUS"
    rp = "RP"
    buy = "BUY"
    sell = "SELL"
    global_event = "GLOBAL"
    campaign = "ADVENTURE"
    council = "ADMIN"
    magewright = "MOD"
    shopkeep = "SHOP"


class Character(object):
    player_id: int
    name: str
    _character_class: CharacterClass
    _faction: Faction
    wealth: int
    experience: int
    level: int
    div_gp: int
    max_gp: int
    div_xp: int
    max_xp: int
    active: bool
    _l1_arena: int
    _l2_arenas: int
    _l1_rps: int
    _l2_rps: int

    def __init__(self, player_id: int, name: str, char_class: CharacterClass,
                 faction: Faction, gold: int, experience: int):
        self.player_id = player_id
        self.name = name
        self._character_class = char_class
        self._faction = faction
        self.wealth = gold
        self.experience = experience

    @classmethod
    def from_dict(cls, char_dict: Dict[str, Any]):
        character = cls(player_id=int(char_dict["Discord ID"]), name=char_dict["Name"],
                        char_class=CharacterClass(char_dict["Class"]), faction=Faction(char_dict["Faction"]),
                        gold=int(char_dict["Current GP"]), experience=int(char_dict["Current XP"]))

        character.div_gp = int(char_dict["Div GP"])
        character.max_gp = int(char_dict["GP Max"])
        character.div_xp = int(char_dict["Weekly XP"])
        character.max_xp = int(char_dict["XP Max"])
        character.active = bool(char_dict["Active"])

        character._l1_arena = int(char_dict["L1 Arena"])
        character._l2_arenas = int(char_dict["L2 Arena 1/2"]) + int(char_dict["L2 Arena 2/2"])
        character._l1_rps = int(char_dict["L1 RP"])
        character._l2_rps = int(char_dict["L2 RP 1/2"]) + int(char_dict["L2 RP 2/2"])

        return character

    @property
    def needed_arenas(self):
        return 1 if self.level == 1 else 2

    @property
    def needed_rps(self):
        return 1 if self.level == 1 else 2

    @property
    def completed_arenas(self):
        return self._l1_arena if self.level == 1 else self._l2_arenas

    @property
    def completed_rps(self):
        return self._l1_rps if self.level == 1 else self._l2_rps

    @property
    def character_class(self) -> str:
        return self._character_class.value

    @property
    def faction(self) -> str:
        return self._faction.value

    @property
    def level(self):
        level = math.ceil((self.experience + 1) / 1000)
        return level if level <= 20 else 20

    def get_member(self, ctx: ApplicationContext) -> discord.Member:
        return discord.utils.get(ctx.guild.members, id=self.player_id)

    def mention(self) -> str:
        return f"<@{self.player_id}>"


class Adventure(object):
    role_id: int
    category_id: int
    name: str
    dm_ids: List[int]
    active: bool

    def __init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_role(self, ctx: ApplicationContext):
        return discord.utils.get(ctx.guild.roles, id=self.role_id)

    def get_category(self, ctx: ApplicationContext):
        return discord.utils.get(ctx.guild.categories, id=self.category_id)

    def get_dm_members(self, ctx: ApplicationContext) -> List[Member] | None:
        dms = [discord.utils.get(ctx.guild.members, id=dm) for dm in self.dm_ids]
        return [dm for dm in dms if dm is not None]

    def get_dm_characters(self, characters: List[Character]) -> List[Character] | None:
        return list(filter(lambda d: d.player_id in self.dm_ids, characters))

    def _get_player_ids(self, ctx: ApplicationContext) -> List[int] | None:
        if role := self.get_role(ctx):
            return [m.id for m in role.members if m.id not in self.dm_ids]
        return None

    def get_player_members(self, ctx: ApplicationContext) -> List[Member] | None:
        if role := self.get_role(ctx):
            return list(filter(lambda p: p.id not in self.dm_ids, role.members))
        return None

    def get_player_characters(self, ctx: ApplicationContext, characters: List[Character]) -> List[Character] | None:
        if player_ids := self._get_player_ids(ctx):
            return list(filter(lambda p: p.player_id in player_ids, characters))


class LogEntry(object):
    author: str
    character: Character
    activity: Activity
    outcome: str | int
    gp: int
    xp: int

    def __init__(self, author: str, character: Character, activity: Activity,
                 outcome: int | str = None, gp: int = None, xp: int = None):
        """
        Base object to log an activity to the BPdia Log worksheet.
        Don't call this directly unless you have a very good reason to do so

        :param author: member.name of the user who initiated the log command. "Blind Prophet" for bot-initiated commands
        :param character: Character who participated in the activity
        :param activity: The type of activity being logged
        :param outcome: The outcome of the activity
        :param gp: Gold override for certain activity types
        :param xp: Experience override for certain activity types
        """

        self.author = author
        self.character = character
        self.activity = activity
        self.outcome = outcome
        self.gp = gp
        self.xp = xp

    def to_sheets_row(self) -> List[str | int]:
        """
        Formats the LogEntry object into the format that gspread/BPdia excepts

        :return: List of objects representing columns in the row being to the BPdia log
        """

        return [
            self.author,
            datetime.datetime.utcnow().isoformat(),
            str(self.character.player_id),
            self.activity.value,
            self.outcome if self.outcome is not None else '',
            self.gp if self.gp is not None else '',
            self.xp if self.gp is not None else '',
            self.character.level
        ]


class ArenaEntry(LogEntry):
    def __init__(self, author: str, character: Character, outcome: str):
        """
        Log Entry for an Arena activity

        :param author: Name of the individual who initiated the command. Formatted as "username#1234"
        :param character: Character object the activity is being logged for
        :param outcome: The arena outcome; "WIN", "LOSS", or "BONUS
        """
        super().__init__(author, character, Activity.arena, outcome)


class BonusEntry(LogEntry):
    def __init__(self, author: str, character: Character, reason: str, gp: int, xp: int):
        """
        Log Entry for a Bonus activity

        :param author: Name of the individual who initiated the command. Formatted as "username#1234"
        :param character: Character object the activity is being logged for
        :param reason: The reason for the bonus being awarded
        :param gp: Amount of bonus gold awarded
        :param xp: amount of bonus experience awarded
        """
        super().__init__(author, character, Activity.bonus, reason, gp, xp)


class RpEntry(LogEntry):
    def __init__(self, author: str, character: Character):
        super().__init__(author, character, Activity.rp)


class BuyEntry(LogEntry):
    def __init__(self, author: str, character: Character, item: str, cost: int):
        super().__init__(author, character, Activity.buy, item, cost)


class SellEntry(LogEntry):
    def __init__(self, author: str, character: Character, item: str, cost: int):
        super().__init__(author, character, Activity.sell, item, cost)


class GlobalEntry(LogEntry):
    def __init__(self, author: str, character: Character, global_name: str, gp: int, xp: int):
        super().__init__(author, character, Activity.global_event, global_name, gp, xp)


class CampaignEntry(LogEntry):
    is_dm: bool
    ep: int

    def __init__(self, author: Member, character: Character, campaign_name: str, ep: int, is_dm: bool):
        self.is_dm = is_dm
        author_formatted = f"{author.name}#{author.discriminator}"
        gp = int(character.max_gp / 2) * ep
        xp = int(character.max_xp / 2) * ep
        if is_dm:
            gp = int(gp * 1.2)
            xp = int(xp * 1.2)
        super().__init__(author_formatted, character, Activity.campaign, f"{campaign_name} - {ep} EP", gp, xp)


class CouncilEntry(LogEntry):
    def __init__(self, author: str, character: Character):
        super().__init__(author, character, Activity.council)


class MagewrightEntry(LogEntry):
    def __init__(self, author: str, character: Character):
        super().__init__(author, character, Activity.magewright)


class ShopkeepEntry(LogEntry):
    def __init__(self, author: str, character: Character):
        super().__init__(author, character, Activity.shopkeep)
