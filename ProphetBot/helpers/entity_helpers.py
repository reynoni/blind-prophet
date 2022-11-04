import bisect
from datetime import datetime
from statistics import mean
from typing import Optional, List

import aiopg
import discord
from discord import ApplicationContext, Member, Role

from ProphetBot.compendium import Compendium
from ProphetBot.models.db_objects import PlayerGuild, PlayerCharacter, PlayerCharacterClass, Activity, DBLog, LevelCaps, \
    Adventure, Arena
from ProphetBot.models.embeds import ArenaStatusEmbed
from ProphetBot.models.schemas import GuildSchema, CharacterSchema, PlayerCharacterClassSchema, LogSchema, \
    AdventureSchema, ArenaSchema
from ProphetBot.queries import get_guild, insert_new_guild, get_log_by_player_and_activity, get_active_character, \
    get_character_class, update_guild, update_character, insert_new_log, get_adventure_by_category_channel_id, \
    get_arena_by_channel, get_multiple_characters, update_arena, get_adventure_by_role_id


async def get_or_create_guild(ctx: ApplicationContext) -> PlayerGuild:
    """
    Retrieves the PlayerGuild object for the current server, or will create a shell object if not found

    :param ctx: Context
    :return: PlayerGuild
    """
    async with ctx.bot.db.acquire() as conn:
        results = await conn.execute(get_guild(ctx.guild.id))
        g_row = await results.first()

    if g_row is None:
        g = PlayerGuild(id=ctx.guild_id, max_level=3, server_xp=0, weeks=0, week_xp=0, max_reroll=1)

        async with ctx.bot.db.acquire() as conn:
            results = await conn.execute(insert_new_guild(g))
            g_row = await results.first()

    g: PlayerGuild = GuildSchema().load(g_row)

    return g


async def remove_fledgling_role(ctx: ApplicationContext, member: Member, reason: Optional[str]):
    """
    Removes the Fledgling role from the given member

    :param ctx: Context
    :param member: Member to remove the role from
    :param reason: Reason in the audit to remove the role
    """
    fledgling_role = discord.utils.get(ctx.guild.roles, name="Fledgling")
    if fledgling_role and (fledgling_role in member.roles):
        await member.remove_roles(fledgling_role, reason=reason)


async def get_character_quests(ctx: ApplicationContext, character: PlayerCharacter) -> PlayerCharacter:
    async with ctx.bot.db.acquire() as conn:
        rp_list = await conn.execute(
            get_log_by_player_and_activity(character.id, ctx.bot.compendium.get_object("c_activity", "RP").id))
        arena_list = await conn.execute(
            get_log_by_player_and_activity(character.id,
                                           ctx.bot.compendium.get_object("c_activity", "ARENA").id))

    character.completed_rps = rp_list.rowcount if character.get_level() == 1 else rp_list.rowcount - 1 if rp_list.rowcount > 0 else 0
    character.needed_rps = 1 if character.get_level() == 1 else 2
    character.completed_arenas = arena_list.rowcount if character.get_level() == 1 else arena_list.rowcount - 1 if arena_list.rowcount > 0 else 0
    character.needed_arenas = 1 if character.get_level() == 1 else 2

    return character


async def get_character(ctx: ApplicationContext, player_id: int, guild_id: int) -> PlayerCharacter | None:
    async with ctx.bot.db.acquire() as conn:
        results = await conn.execute(get_active_character(player_id, guild_id))
        row = await results.first()

    if row is None:
        return None
    else:
        character: PlayerCharacter = CharacterSchema(ctx.bot.compendium).load(row)
        return character


async def get_player_character_class(ctx: ApplicationContext, char_id: int) -> List[PlayerCharacterClass] | None:
    class_ary = []

    async with ctx.bot.db.acquire() as conn:
        async for row in conn.execute(get_character_class(char_id)):
            if row is not None:
                char_class: PlayerCharacterClass = PlayerCharacterClassSchema(ctx).load(row)
                class_ary.append(char_class)

    if len(class_ary) < 1:
        return None
    else:
        return class_ary


def get_activity_amount(character: PlayerCharacter, activity: Activity, cap: LevelCaps, g: PlayerGuild, gold: int,
                        xp: int):
    if activity.ratio is not None:
        # Calculate the ratio unless we have a manual override
        reward_gold = cap.max_gold * activity.ratio if gold == 0 else gold
        reward_xp = cap.max_xp * activity.ratio if xp == 0 else xp
    else:
        reward_gold = gold
        reward_xp = xp

    max_xp = (g.max_level - 1) * 1000
    server_xp, char_gold, char_xp = 0, 0, 0

    if activity.diversion:  # Apply diversion limits
        if character.div_gold + reward_gold > cap.max_gold:
            char_gold = 0 if cap.max_gold - character.div_gold < 0 else cap.max_gold - character.div_gold
        else:
            char_gold = reward_gold

        if character.div_xp + reward_xp > cap.max_xp:
            xp = 0 if cap.max_xp - character.div_xp < 0 else cap.max_xp - character.div_xp
        else:
            xp = reward_xp
    else:
        char_gold = reward_gold
        xp = reward_xp

    # Guild Server Stats
    if character.xp + xp >= max_xp:
        char_xp = 0 if max_xp - character.xp < 0 else max_xp - character.xp
        server_xp = 0 if xp - char_xp < 0 else xp - char_xp
    else:
        char_xp = xp

    return char_gold, char_xp, server_xp


async def create_logs(ctx: ApplicationContext, character: PlayerCharacter, activity: Activity, notes: str = None,
                      gold: int = 0, xp: int = 0) -> DBLog:
    cap: LevelCaps = ctx.bot.compendium.get_object("c_level_caps", character.get_level())
    g: PlayerGuild = await get_or_create_guild(ctx)

    char_gold, char_xp, server_xp = get_activity_amount(character, activity, cap, g, gold, xp)

    char_log = DBLog(author=ctx.author.id, xp=char_xp, gold=char_gold, character_id=character.id, activity=activity,
                     notes=notes)
    character.gold += char_gold
    character.xp += char_xp
    g.week_xp += server_xp

    if activity.diversion:
        character.div_gold += char_gold
        character.div_xp += char_xp

    async with ctx.bot.db.acquire() as conn:
        results = await conn.execute(insert_new_log(char_log))
        row = await results.first()
        await conn.execute(update_character(character))
        await conn.execute(update_guild(g))

    log_entry: DBLog = LogSchema(ctx).load(row)

    return log_entry


async def update_dm(dm: Member, category_permissions: dict, role: Role, adventure_name: str,
                    remove: bool = False) -> dict:
    if remove:
        await dm.remove_roles(role, reason=f"Removed from adventure {adventure_name}")
        del category_permissions[dm]
    else:
        await dm.add_roles(role, reason=f"Creating/Modifying adventure {adventure_name}")
        category_permissions[dm] = discord.PermissionOverwrite(manage_messages=True)

    return category_permissions


async def get_adventure(ctx: ApplicationContext) -> Adventure | None:
    async with ctx.bot.db.acquire() as conn:
        results = await conn.execute(get_adventure_by_category_channel_id(ctx.channel.category_id))
        row = await results.first()

    if row is None:
        return None
    else:
        adventure: Adventure = AdventureSchema(ctx).load(row)
        return adventure


async def get_adventure_from_role(ctx: ApplicationContext, role_id: int) -> Adventure | None:
    async with ctx.bot.db.acquire() as conn:
        results = await conn.execute(get_adventure_by_role_id(role_id))
        row = await results.first()

    if row is None:
        return None
    else:
        adventure: Adventure = AdventureSchema(ctx).load(row)
        return adventure


async def get_arena(db: aiopg.sa.Engine, channel_id: int, compendium) -> Arena | None:
    async with db.acquire() as conn:
        results = await conn.execute(get_arena_by_channel(channel_id))
        row = await results.first()

    if row is None:
        return None
    else:
        arena: Arena = ArenaSchema(compendium).load(row)
        return arena


async def remove_post_from_arena_board(ctx: ApplicationContext | discord.Interaction, member: Member):
    def predicate(message):
        return message.author == member

    if arena_board := discord.utils.get(ctx.guild.channels, name='arena-board'):
        try:
            deleted_message = await arena_board.purge(check=predicate)
            print(f'{len(deleted_message)} messages by {member.name} deleted from #{arena_board.name}')
        except Exception as error:
            if isinstance(error, discord.errors.HTTPException):
                await ctx.send(f'Warning: deleting users\'s post(s) from {arena_board.mention} failed')
            else:
                print(error)


async def add_player_to_arena(ctx: discord.Interaction, player: Member, arena: Arena,
                              db: aiopg.sa.Engine, compendium: Compendium):
    await player.add_roles(arena.get_role(ctx))
    await remove_post_from_arena_board(ctx, player)

    await ctx.response.send_message(f"{player.mention} has joined the arena!", ephemeral=False)

    await update_arena_tier(ctx, db, arena, compendium)

    await update_arena_status(ctx, arena)


async def update_arena_tier(ctx: discord.Interaction, db: aiopg.sa.Engine, arena: Arena, compendium: Compendium):
    players = [p.id for p in list(set(filter(lambda p: p.id != arena.host_id,
                                             arena.get_role(ctx).members)))]

    if len(players) > 0:
        chars = []
        async with db.acquire() as conn:
            async for row in await conn.execute(get_multiple_characters(players, ctx.guild_id)):
                if row is not None:
                    character: PlayerCharacter = CharacterSchema(compendium).load(row)
                    chars.append(character)
        avg_level = mean(c.get_level() for c in chars)
        tier = bisect.bisect([t.avg_level for t in compendium.c_arena_tier], avg_level)
        arena.tier = compendium.get_object("c_arena_tier", tier)

        async with db.acquire() as conn:
            await conn.execute(update_arena(arena))


async def update_arena_status(ctx: ApplicationContext | discord.Interaction, arena: Arena):
    embed = ArenaStatusEmbed(ctx, arena)

    msg: discord.Message = await ctx.channel.fetch_message(arena.pin_message_id)

    if msg:
        await msg.edit(embed=embed)


async def end_arena(ctx: ApplicationContext, arena: Arena):
    for member in arena.get_role(ctx).members:
        await member.remove_roles(arena.get_role(ctx), reason=f"Arena complete")

    arena.end_ts = datetime.utcnow()

    async with ctx.bot.db.acquire() as conn:
        await conn.execute(update_arena(arena))

    msg: discord.Message = await ctx.channel.fetch_message(arena.pin_message_id)

    if msg:
        await msg.delete(reason="Closing arena")

    await ctx.respond("Arena closed. This channel is now free for use")


def get_faction_roles(ctx: ApplicationContext, player: Member) -> List[Role] | None:
    faction_names = [f.value for f in ctx.bot.compendium.c_faction]
    faction_names.remove("Guild Initiate")
    faction_names.remove("Guild Member")

    roles = list(filter(lambda r: r.name in faction_names, player.roles))

    if len(roles) == 0:
        return None
    return roles






