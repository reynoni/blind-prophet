import datetime
import enum
import math
from math import floor
from typing import Dict, Any

import discord
from discord.ext import commands
from discord.commands.context import ApplicationContext
from discord import OptionChoice


class CommandOptionEnum(enum.Enum):

    @classmethod
    def option_list(cls):
        return list(map(lambda o: OptionChoice(o.value), cls))


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
    INITIATE = 'Initiate'
    FREELANCER = 'Freelancer'
    COPPER_DRAGONS = 'Order of the Copper Dragon'
    SILENT_WHISPERS = 'Silent Whispers'
    SILVER_WOLVES = 'Silver Wolves'
    CRIMSON_BLADES = 'Crimson Blades'
    CLOVER_CONCLAVE = 'Clover Conclave'
    SUNSTONE_LOTUS = 'Sunstone Lotus'
    FALCON_EYES = 'The Falcon Eyes'


class Activity(enum.Enum):
    arena = "ARENA"
    bonus = "BONUS"


def _clean_input(raw_imput):
    header_data = list(raw_imput[0][0])
    char_data = list(raw_imput[1][0])
    cleaned_dict = dict()

    for i in range(len(header_data)):
        if header_data[i] != '':  # Parse out some empty columns
            cleaned_dict[header_data[i]] = str(char_data[i]).replace('*', '1')

    return cleaned_dict


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

    def to_sheets_row(self):
        print(f"self.gp: {self.gp}, self.xp: {self.xp}")

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
        super().__init__(author, character, Activity.arena, outcome)


class BonusEntry(LogEntry):

    def __init__(self, author: str, character: Character, reason: str, gp: int, xp: int):
        super().__init__(author, character, Activity.bonus, reason, gp, xp)
