class CharacterClass(object):
    character_id: int
    character_class: int
    character_subclass: int
    level: int
    primary: bool

class Faction(object):
    id: int
    guild_id: int
    value: int
    role_id: int

class Character(object):
    # Attributes based on queries: total_level, div_gold, max_gold, div_xp, max_xp, l1_arena, l2_arena, l1_rp, l2_rp

    player_id: int
    name: str
    gold: int
    xp: int
    active: bool
    _character_class: [CharacterClass]
    _faction: Faction

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self,key,value)

