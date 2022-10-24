from marshmallow import Schema, fields, post_load
from ProphetBot.models.db_objects import BP_Guild


class guild_schema(Schema):
    id = fields.Integer(data_key="id", required=True)
    max_level = fields.Integer(data_key="max_level", required=True)
    server_xp = fields.Integer(data_key="server_xp", required=True)
    weeks = fields.Integer(data_key="weeks", required=True)
    max_reroll = fields.Integer(data_key="max_reroll", required=True)
    mod_roles = fields.List(fields.Integer, data_key="mod_roles")
    lore_roles = fields.List(fields.Integer, data_key="lore_roles")

    @post_load
    def make_guild(self, data, **kwargs):
        return BP_Guild(**data)
