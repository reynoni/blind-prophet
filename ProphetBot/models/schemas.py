from marshmallow import Schema, fields, post_load, post_dump, pre_load, ValidationError
from ProphetBot.models.sheets_objects import Adventure
from ProphetBot.models.db_objects import RpDashboard


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
