from marshmallow import Schema, fields, post_load

from ProphetBot.models.db_objects.category_objects import *


class c_rarity_schema(Schema):
    id = fields.Integer(data_key="id", required=True)
    value = fields.String(data_key="value", required=True)
    abbreviation = fields.List(fields.String, data_key="abbreviation", required=True)

    @post_load
    def make_c_rarity(self, data, **kwargs):
        return c_rarity(**data)


class c_blacksmith_type_schema(Schema):
    id = fields.Integer(data_key="id", required=True)
    value = fields.String(data_key="value", required=True)

    @post_load
    def make_c_blacksmith_type(self, data, **kwargs):
        return c_blacksmith_type(**data)


class c_consumable_type_schema(Schema):
    id = fields.Integer(data_key="id", required=True)
    value = fields.String(data_key="value", required=True)

    @post_load
    def make_c_consumable_type(self, data, **kwargs):
        return c_consumable_type(**data)


class c_magic_school_schema(Schema):
    id = fields.Integer(data_key="id", required=True)
    value = fields.String(data_key="value", required=True)

    @post_load
    def make_c_magic_school(self, data, **kwargs):
        return c_magic_school(**data)


class c_character_class_schema(Schema):
    id = fields.Integer(data_key="id", required=True)
    value = fields.String(data_key="value", required=True)

    @post_load
    def make_c_character_class(self, data, **kwargs):
        return c_character_class(**data)


class c_character_subclass_schema(Schema):
    id = fields.Integer(data_key="id", required=True)
    parent = fields.Integer(data_key="parent", required=True)
    value = fields.String(data_key="value", required=True)

    @post_load
    def make_c_character_subclass(self, data, **kwargs):
        return c_character_subclass(**data)


class c_character_race_schema(Schema):
    id = fields.Integer(data_key="id", required=True)
    value = fields.String(data_key="value", required=True)

    @post_load
    def make_c_character_race(self, data, **kwargs):
        return c_character_race(**data)


class c_character_subrace_schema(Schema):
    id = fields.Integer(data_key="id", required=True)
    parent = fields.Integer(data_key="parent", required=True)
    value = fields.String(data_key="value", required=True)

    @post_load
    def make_c_character_subrace(self, data, **kwargs):
        return c_character_subrace(**data)


class c_global_modifier_schema(Schema):
    id = fields.Integer(data_key="id", required=True)
    value = fields.String(data_key="value", required=True)
    adjustment = fields.Float(data_key="adjustment", required=True)
    max = fields.Integer(data_key="max", required=True)

    @post_load
    def make_c_global_modifier(self, data, **kwargs):
        return c_global_modifier(**data)


class c_host_status_schema(Schema):
    id = fields.Integer(data_key="id", required=True)
    value = fields.String(data_key="value", required=True)

    @post_load
    def make_c_host_status(self, data, **kwargs):
        return c_host_status(**data)


class c_arena_tier_schema(Schema):
    id = fields.Integer(data_key="id", required=True)
    avg_level = fields.Integer(data_key="avg_level", required=True)
    max_phases = fields.Integer(data_key="max_phases", required=True)

    @post_load
    def make_c_arena_tier(self, data, **kwargs):
        return c_arena_tier(**data)


class c_adventure_tier_schema(Schema):
    id = fields.Integer(data_key="id", required=True)
    avg_level = fields.Integer(data_key="avg_level", required=True)
    max_xp = fields.Integer(data_key="max_xp", required=True)

    @post_load
    def make_c_adventure_tier(self, data, **kwargs):
        return c_adventure_tier(**data)


class c_shop_type_schema(Schema):
    id = fields.Integer(data_key="id", required=True)
    value = fields.String(data_key="value", required=True)
    synonyms = fields.List(fields.String, data_key="synonyms", required=False, default=[])
    tools = fields.List(fields.String, data_key="tools", required=False, default=[])

    @post_load
    def make_c_shop_type(self, data, **kwargs):
        return c_shop_type(**data)


class c_activity_schema(Schema):
    id = fields.Integer(data_key="id", required=True)
    value = fields.String(data_key="value", required=True)
    ratio = fields.Float(data_key="ratio", required=False, default=None)
    diversion = fields.Boolean(data_key="diversion", required=True)

    @post_load
    def make_c_activity(self, data, **kwargs):
        return c_activity(**data)


class c_faction_schema(Schema):
    id = fields.Integer(data_key="id", required=True)
    guild_id = fields.Integer(data_key="guild_id", required=True)
    value = fields.String(data_key="value", required=True)
    role_id = fields.Integer(data_key="role_id", required=True)

    @post_load
    def make_c_faction(self, data, **kwargs):
        return c_faction(**data)


class c_dashboard_type_schema(Schema):
    id = fields.Integer(data_key="id", required=True)
    value = fields.String(data_key="value", required=True)

    @post_load
    def make_c_dashboard_type(self, data, **kwargs):
        return c_dashboard_type(**data)


class c_level_caps_schema(Schema):
    level = fields.Integer(data_key="level", required=True)
    max_gold = fields.Integer(data_key="max_gold", required=True)
    max_xp = fields.Integer(data_key="max_xp", required=True)

    @post_load
    def make_level_caps(self, data, **kwargs):
        return c_level_caps(**data)
