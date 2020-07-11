from ProphetBot.constants import *


def is_tracker(ctx):
    return TRACKERS_ROLE in map(lambda role: role.id, ctx.message.author.roles)


def is_council(ctx):
    return COUNCIL_ROLE in map(lambda role: role.id, ctx.message.author.roles)


def is_admin(ctx):
    return ctx.author.id in ADMIN_USERS
