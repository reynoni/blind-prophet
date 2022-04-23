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
    GATEKEEPER = 'Gatekeeper'
    STARLIGHT = 'Starlight Scholar'
    FREELANCER = 'Freelancer'
    ADEPT = 'Adept'
    INITIATE = 'Initiate'


def _clean_input(raw_imput):
    header_data = list(raw_imput[0][0])
    char_data = list(raw_imput[1][0])
    cleaned_dict = dict()

    for i in range(len(header_data)):
        if header_data[i] != '':  # Parse out some empty columns
            cleaned_dict[header_data[i]] = str(char_data[i]).replace('*', '1')

    return cleaned_dict


class Character(object):

    def __init__(self, raw_input):
        char_dict = _clean_input(raw_input)
        self.player_id = int(char_dict["Discord ID"])
        self.name = char_dict["Name"]
        self._character_class = CharacterClass(char_dict["Class"].title())
        self._faction = Faction(char_dict["Faction"].title())
        self.level = int(char_dict["Level"])
        self.wealth = int(char_dict["Total GP"])
        self.experience = int(char_dict["Total XP"])
        self.image_link = char_dict.get("Image URL")
        self.sheet_link = char_dict.get("Sheet URL")

        self.div_gp = int(char_dict["Div GP"])
        self.max_gp = int(char_dict["GP Max"])
        self.div_xp = int(char_dict["Div XP"])
        self.max_xp = int(char_dict["XP Max"])
        self.asl_mod = char_dict["ASL Mod"]
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
