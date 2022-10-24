class c_rarity(object):
    def __init__(self, id, value, abbreviation):
        """
        :param id: int
        :param value: str
        :param abbreviation: List[str]
        """

        self.id = id
        self.value = value
        self.abbreviation = abbreviation


class c_blacksmith_type(object):
    def __init__(self, id, value):
        """
        :param id: int
        :param value: str
        """

        self.id = id
        self.value = value


class c_consumable_type(object):
    def __init__(self, id, value):
        """
        :param id: int
        :param value: str
        """

        self.id = id
        self.value = value


class c_magic_school(object):
    def __init__(self, id, value):
        """
        :param id: int
        :param value: str
        """

        self.id = id
        self.value = value


class c_character_class(object):
    def __init__(self, id, value):
        """
        :param id: int
        :param value: str
        """

        self.id = id
        self.value = value


class c_character_subclass(object):
    def __init__(self, id, parent, value):
        """
        :param id: int
        :param parent: int
        :param value: str
        """

        self.id = id
        self.parent = parent
        self.value = value


class c_character_race(object):
    def __init__(self, id, value):
        """
        :param id: int
        :param value: str
        """

        self.id = id
        self.value = value


class c_character_subrace(object):
    def __init__(self, id, parent, value):
        """
        :param id: int
        :param parent: int
        :param value: str
        """

        self.id = id
        self.parent = parent
        self.value = value


class c_global_modifier(object):
    def __init__(self, id, value, adjustment, max):
        """
        :param id: int
        :param value: str
        :param adjustment: float
        :param max: int
        """

        self.id = id
        self.value = value
        self.adjustment = adjustment
        self.max = max


class c_host_status(object):
    def __init__(self, id, value):
        """
        :param id: int
        :param value: str
        """

        self.id = id
        self.value = value


class c_arena_tier(object):
    def __init__(self, id, avg_level, max_phases):
        """
        :param id: int
        :param avg_level: int
        :param max_phases: int
        """

        self.id = id
        self.avg_level = avg_level
        self.max_phases = max_phases


class c_adventure_tier(object):
    def __init__(self, id, avg_level, max_xp):
        """
        :param id: int
        :param avg_level: int
        :param max_xp: int
        """

        self.id = id
        self.avg_level = avg_level
        self.max_xp = max_xp

class c_shop_type(object):
    def __init__(self, id, value, synonyms, tools):
        """
        :param id: int
        :param value: str
        :param synonyms: List[str]
        :param tools: List[str]
        """

        self.id = id
        self.value = value
        self.synonyms = synonyms
        self.tools = tools


class c_activity(object):
    def __init__(self, id, value, ratio, diversion):
        """
        :param id: int
        :param value: str
        :param ratio: float
        :param diversion: bool
        """

        self.id = id
        self.value = value
        self.ratio = ratio
        self.diversion = diversion


class c_faction(object):
    def __init__(self, id, guild_id, value, role_id):
        """
        :param id: int
        :param guild_id: int
        :param value: str
        :param role_id: int
        """

        self.id = id
        self.guild_id = guild_id
        self.value = value
        self.role_id = role_id


class c_dashboard_type(object):
    def __init__(self, id, value):
        """
        :param id: int
        :param value: str
        """

        self.id = id
        self.value = value


class c_level_caps(object):
    def __init__(self, level, max_gold, max_xp):
        """
        :param level: int
        :param max_gold: int
        :param max_xp: int
        """

        self.level = level
        self.max_gold = max_gold
        self.max_xp = max_xp
