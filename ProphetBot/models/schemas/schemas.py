from marshmallow import Schema, fields, post_load, post_dump, pre_load, ValidationError
from ProphetBot.models.sheets_objects import Adventure
from ProphetBot.models.db_objects import *


class AdventureSchema(Schema):
    role_id = fields.Integer(data_key='Adventure Role ID', required=True)
    category_id = fields.Integer(data_key='CategoryChannel ID', required=True)
    name = fields.String(data_key='Adventure Name', required=True)
    dm_ids = fields.List(fields.Integer, data_key='DMs', required=True)
    active = fields.Boolean(data_key='Active', default=True)

    @pre_load
    def split_dms(self, data, **kwargs):
        if 'DMs' not in data:
            raise ValidationError("Input data must have one or more DMs")
        data['DMs'] = data['DMs'].split(', ')
        return data

    @post_load
    def make_adventure(self, data, **kwargs):
        return Adventure(**data)

    @post_dump
    def to_list(self, data, many, **kwargs):
        formatted_dms = ', '.join(data['DMs'])
        return [
            data['Adventure Role ID'],
            data['CategoryChannel ID'],
            data['Adventure Name'],
            formatted_dms,
            data['Active']
        ]


class RpDashboardSchema(Schema):
    id = fields.Integer(data_key='id', required=True)
    category_id = fields.Integer(data_key='categorychannel_id', required=True)
    post_channel_id = fields.Integer(data_key='dashboard_post_channel_id', required=True)
    post_id = fields.Integer(data_key='dashboard_post_id', required=True)
    excluded_channels = fields.List(fields.Integer, data_key='excluded_channel_ids', load_default=[])

    @post_load
    def make_rpdashboard(self, data, **kwargs):
        return RpDashboard(**data)


class gEventSchema(Schema):
    event_id = fields.Integer(data_key='id', required=True)
    guild_id = fields.Integer(data_key='guild_id', required=True)
    name = fields.String(data_key='name', required=True)
    base_gold = fields.Integer(data_key='base_gold', required=True)
    base_exp = fields.Integer(data_key='base_exp', required=True)
    base_mod = fields.String(data_key='base_mod', required=True)
    combat = fields.Boolean(data_key='combat', required=True)
    channels = fields.List(fields.Integer, data_key='channels', load_default=[], required=False)
    active = fields.Boolean(data_key='active', required=True)

    @post_load
    def make_globEvent(self, data, **kwargs):
        return gEvent(**data)


class gPlayerSchema(Schema):
    id = fields.Integer(data_key='id', required=True)
    player_id = fields.Integer(data_key='player_id', required=True)
    global_id = fields.Integer(data_key='global_id', required=True)
    modifier = fields.String(data_key='modifier', required=False, load_default=None)
    host = fields.String(data_key='host', required=False, load_default=None)
    gold = fields.Integer(data_key='gold', required=True)
    exp = fields.Integer(data_key='exp', required=True)
    update = fields.Boolean(data_key='update', required=True)
    active = fields.Boolean(data_key='active', required=True)

    @post_load
    def make_globEvent(self, data, **kwargs):
        return gPlayer(**data)
