from marshmallow import Schema, fields, post_load

from ProphetBot.models.db_objects.ref_objects import *


class RefCategoryDashboardSchema(Schema):
    category_channel_id = fields.Integer(data_key="category_channel_id", required=True)
    dashboard_post_channel_id = fields.Integer(data_key="dashboard_post_channel_id", required=True)
    dashboard_post_id = fields.Integer(data_key="dashboard_post_id", required=True)
    excluded_channel_ids = fields.List(fields.Integer, data_key="excluded_channel_ids")
    dashboard_type = fields.Integer(data_key="dashboard_type", required=True)

    @post_load
    def make_dashboard(self, data, **kwargs):
        return RefCategoryDashboard(**data)


class RefWeeklyStipendSchema(Schema):
    role_id = fields.Integer(data_key="role_id", required=True)
    guild_id = fields.Integer(data_key="guild_id", required=True)
    ratio = fields.Float(data_key="ratio", required=True)
    reason = fields.String(data_key="reason", required=False, allow_none=True)

    @post_load
    def make_stipend(self, data, **kwargs):
        return RefWeeklyStipend(**data)



