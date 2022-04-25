import datetime
import enum

import discord
from discord.ext import commands


class CharacterClass(enum.Enum):
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


class Faction(enum.Enum):
    BOROMAR_CAPTAIN = 'Boromar Captain'
    REDCLOAK_CAPTAIN = 'Redcloak Captain'
    GATEKEEPERS_CAPTAIN = 'Gatekeepers Captain'
    MAGISTER_CAPTAIN = 'Magister Captain'

    BOROMAR = 'Boromar'
    REDCLOAK = 'Redcloak'
    DIRECTORATE = 'Directorate'
    GATEKEEPER = 'Gatekeeper'
    STARLIGHT = 'Starlight'
    FREELANCER = 'Freelancer'
    ADEPT = 'Adept'
    INITIATE = 'Initiate'


class Activity(enum.Enum):
    arena = "ARENA"


def _clean_input(raw_imput):
    header_data = list(raw_imput[0][0])
    char_data = list(raw_imput[1][0])
    cleaned_dict = dict()

    for i in range(len(header_data)):
        if header_data[i] != '':  # Parse out some empty columns
            cleaned_dict[header_data[i]] = str(char_data[i]).replace('*', '1')

    return cleaned_dict


class Character(object):

    def __init__(self, char_dict):
        # char_dict = _clean_input(raw_input)
        self.player_id = int(char_dict["Discord ID"])
        self.name = char_dict["Name"]
        self._character_class = CharacterClass(char_dict["Class"].title())
        self._faction = Faction(char_dict["Faction"].title())
        self.level = int(char_dict["Level"])
        self.wealth = int(char_dict["Current GP"])
        self.experience = int(char_dict["Current XP"])
        self.image_link = char_dict.get("Image URL")
        self.sheet_link = char_dict.get("Sheet URL")

        self.div_gp = int(char_dict["Div GP"])
        self.max_gp = int(char_dict["GP Max"])
        self.div_xp = int(char_dict["Weekly XP"])
        self.max_xp = int(char_dict["XP Max"])
        self.active = char_dict["Active"]

        if self.level < 3:
            self.needed_arenas = 1 if self.level == 1 else 2
            self.needed_rps = 1 if self.level == 1 else 2
            self.completed_arenas = int(char_dict["L1 Arena"]) if self.level == 1 else (
                    int(char_dict["L2 Arena 1/2"]) + int(char_dict["L2 Arena 2/2"]))
            self.completed_rps = int(char_dict["L1 RP"]) if self.level == 1 else (
                    int(char_dict["L2 RP 1/2"]) + int(char_dict["L2 RP 2/2"]))

    @property
    def character_class(self):
        return self._character_class.value

    @property
    def faction(self):
        return self._faction.value

    async def get_member(self, ctx: commands.Context) -> discord.Member:
        member_converter = commands.MemberConverter()
        return await member_converter.convert(ctx, self.player_id)


class LogEntry(object):
    author: str
    character: Character
    activity: Activity
    outcome: str | int
    gp: int
    xp: int

    def __init__(self, author: str, character: Character, activity: Activity, outcome: int | str = None,
                      gp: int = None, xp: int = None):
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

    def to_sheets_row(self, server_level: int):
        return [
            self.author,
            datetime.datetime.utcnow(),
            self.character.player_id,
            self.activity,
            self.outcome or '',
            self.gp or '',
            self.xp or '',
            self.character.level,
            server_level
        ]


class ArenaEntry(LogEntry):

    def __init__(self, author: str, character: Character, outcome: str):
        super().__init__(author, character, Activity.arena, outcome)

