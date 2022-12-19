import bisect
import re
from datetime import datetime
from statistics import mean

import aiopg
import discord
from discord import ApplicationContext, Member, Role, Bot, Client
from texttable import Texttable

from ProphetBot.compendium import Compendium
from ProphetBot.models.db_objects import PlayerGuild, PlayerCharacter, Adventure, Arena, PlayerCharacterClass
from ProphetBot.models.embeds import ArenaStatusEmbed
from ProphetBot.models.schemas import GuildSchema, CharacterSchema, AdventureSchema, ArenaSchema, \
    PlayerCharacterClassSchema
from ProphetBot.queries import get_guild, insert_new_guild, get_adventure_by_category_channel_id, \
    get_arena_by_channel, get_multiple_characters, update_arena, get_adventure_by_role_id, get_characters, \
    get_logs_in_past, get_character_class


async def get_or_create_guild(db: aiopg.sa.Engine, guild_id: int) -> PlayerGuild:
    """
    Retrieves the PlayerGuild object for the current server, or will create a shell object if not found

    :param db: DB Engine
    :param guild_id:  Guild ID
    :return: PlayerGuild
    """
    async with db.acquire() as conn:
        results = await conn.execute(get_guild(guild_id))
        g_row = await results.first()

    if g_row is None:
        g = PlayerGuild(id=guild_id, max_level=3, server_xp=0, weeks=0, week_xp=0, max_reroll=1)

        async with db.acquire() as conn:
            results = await conn.execute(insert_new_guild(g))
            g_row = await results.first()

    g: PlayerGuild = GuildSchema().load(g_row)

    return g


async def update_dm(dm: Member, category_permissions: dict, role: Role, adventure_name: str,
                    remove: bool = False) -> dict:
    """
    Adds/removes a DM from an adventure

    :param dm: Member to add/remove
    :param category_permissions: PermissionOverWrite
    :param role: Role of the Adventure
    :param adventure_name: Name of the adventure for audit purposes
    :param remove: True to remove dm, otherwise add the dm
    :return: Updated PermissionOverwrite dict
    """
    if remove:
        await dm.remove_roles(role, reason=f"Removed from adventure {adventure_name}")
        del category_permissions[dm]
    else:
        await dm.add_roles(role, reason=f"Creating/Modifying adventure {adventure_name}")
        category_permissions[dm] = discord.PermissionOverwrite(manage_messages=True)

    return category_permissions


async def get_adventure(bot: Bot, category_id: int) -> Adventure | None:
    """
    Retrieves the Adventure for the given category_ic

    :param bot: Bot
    :param category_id: Channel Category ID of the Adventure
    :return: Adventure if found, else None
    """
    async with bot.db.acquire() as conn:
        results = await conn.execute(get_adventure_by_category_channel_id(category_id))
        row = await results.first()

    if row is None:
        return None
    else:
        adventure: Adventure = AdventureSchema(bot.compendium).load(row)
        return adventure


async def get_adventure_from_role(bot: Bot, role_id: int) -> Adventure | None:
    """
    Get the Adventure given the role

    :param bot: Bot
    :param role_id: Role id
    :return: Adventure if found, else None
    """
    async with bot.db.acquire() as conn:
        results = await conn.execute(get_adventure_by_role_id(role_id))
        row = await results.first()

    if row is None:
        return None
    else:
        adventure: Adventure = AdventureSchema(bot.compendium).load(row)
        return adventure


async def get_arena(bot: Bot | Client, channel_id: int) -> Arena | None:
    """
    Get the active Arena for the given channel

    :param bot: Bot or Client
    :param channel_id: TextChannel id to get the arena for
    :return: Arena if found, else None
    """
    async with bot.db.acquire() as conn:
        results = await conn.execute(get_arena_by_channel(channel_id))
        row = await results.first()

    if row is None:
        return None
    else:
        arena: Arena = ArenaSchema(bot.compendium).load(row)
        return arena


async def remove_post_from_arena_board(ctx: ApplicationContext | discord.Interaction, member: Member):
    """
    Removes a Member's post from the arena-board channel

    :param ctx: Context
    :param member: Member
    """

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
    """
    Adds a player to the Arena

    :param ctx: Context
    :param player: Member to add
    :param arena: Arena to add the player to
    :param db: Engine
    :param compendium: Compendium for category reference
    """
    await player.add_roles(arena.get_role(ctx))
    await remove_post_from_arena_board(ctx, player)

    await ctx.response.send_message(f"{player.mention} has joined the arena!", ephemeral=False)

    await update_arena_tier(ctx, db, arena, compendium)

    await update_arena_status(ctx, arena)


async def update_arena_tier(ctx: discord.Interaction, db: aiopg.sa.Engine, arena: Arena, compendium: Compendium):
    """
    Recalculates and updates the arena tier

    :param ctx: Context
    :param db: Engine
    :param arena: Arena
    :param compendium: Compendium
    """
    players = [p.id for p in list(set(filter(lambda p: p.id != arena.host_id,
                                             arena.get_role(ctx).members)))]

    if len(players) > 0:
        chars = []
        async with db.acquire() as conn:
            async for row in await conn.execute(get_multiple_characters(players, ctx.guild_id)):
                if row is not None:
                    character: PlayerCharacter = CharacterSchema(compendium).load(row)
                    chars.append(character)
        if len(chars) > 0:
            avg_level = mean(c.get_level() for c in chars)
            tier = bisect.bisect([t.avg_level for t in list(compendium.c_arena_tier[0].values())], avg_level)
            arena.tier = compendium.get_object("c_arena_tier", tier)

            async with db.acquire() as conn:
                await conn.execute(update_arena(arena))


async def update_arena_status(ctx: ApplicationContext | discord.Interaction, arena: Arena):
    """
    Updates the ArenaStatusEmbed

    :param ctx: Context
    :param arena: Arena
    """
    embed = ArenaStatusEmbed(ctx, arena)

    msg: discord.Message = await ctx.channel.fetch_message(arena.pin_message_id)

    if msg:
        await msg.edit(embed=embed)


async def end_arena(ctx: ApplicationContext, arena: Arena):
    """
    Ends the current arena

    :param ctx: Context
    :param arena: Arena
    """
    for member in arena.get_role(ctx).members:
        await member.remove_roles(arena.get_role(ctx), reason=f"Arena complete")

    arena.end_ts = datetime.utcnow()

    async with ctx.bot.db.acquire() as conn:
        await conn.execute(update_arena(arena))

    msg: discord.Message = await ctx.channel.fetch_message(arena.pin_message_id)

    if msg:
        await msg.delete(reason="Closing arena")

    await ctx.respond("Arena closed. This channel is now free for use")


async def get_guild_character_summary_stats(bot: Bot, guild_id: int):
    inactive = []
    chars = []
    total = 0

    async with bot.db.acquire() as conn:
        async for row in await conn.execute(get_characters(guild_id)):
            if row is not None:
                character: PlayerCharacter = CharacterSchema(bot.compendium).load(row)
                chars.append(character)
                total += 1

    if len(chars) > 0:
        for c in chars:
            async with bot.db.acquire() as conn:
                results = await conn.execute(get_logs_in_past(c.id))
                row = await results.first()

            if row is None:
                inactive.append(c)

    if len(inactive) == 0:
        inactive = None

    return total, inactive


async def get_guild_character_census_stats(bot: Bot, guild_id: int):
    races = dict()
    classes = dict()
    race_data = []
    class_data = []

    # Setup our census dicts
    for race in bot.compendium.c_character_race[0].values():
        subraces = dict()
        subraces['None'] = 0
        subraces["Total"] = 0

        for subrace in list(filter(lambda s: s.parent == race.id, bot.compendium.c_character_subrace[0].values())):
            subraces[subrace.value] = 0
        races[race.value] = subraces

    for cl in bot.compendium.c_character_class[0].values():
        subclasses = dict()
        subclasses['None'] = 0
        subclasses["Total"] = 0

        for subclass in list(filter(lambda s: s.parent == cl.id, bot.compendium.c_character_subclass[0].values())):
            subclasses[subclass.value] = 0
        classes[cl.value] = subclasses

    async with bot.db.acquire() as conn:
        async for row in await conn.execute(get_characters(guild_id)):
            if row is not None:
                character: PlayerCharacter = CharacterSchema(bot.compendium).load(row)
                races[character.race.value]["Total"] += 1

                if character.subrace is None:
                    races[character.race.value]["None"] += 1
                else:
                    races[character.race.value][character.subrace.value] += 1

                async for line in await conn.execute(get_character_class(character.id)):
                    if line is not None:
                        char_class: PlayerCharacterClass = PlayerCharacterClassSchema(bot.compendium).load(line)
                        classes[char_class.primary_class.value]["Total"] += 1

                        if char_class.subclass is None:
                            classes[char_class.primary_class.value]["None"] += 1
                        else:
                            classes[char_class.primary_class.value][char_class.subclass.value] += 1

    for k, v in races.items():
        race_data.append([f"**{k}**", str(races[k]['Total'])])
        for sr in v:
            race_data.append([f"\u200b{sr}", str(races[k][sr])])

    for k, v in classes.items():
        class_data.append([f"**{k}**", str(classes[k]['Total'])])
        for sc in v:
            class_data.append([f"\u200b{sc}", str(classes[k][sc])])

    return race_data, class_data


def build_table(matches, result_map, headers):
    table = Texttable()
    if len(matches) > 1:
        table.set_deco(Texttable.HEADER | Texttable.HLINES | Texttable.VLINES)
        table.set_cols_align(['c'] * len(headers))
        table.set_cols_valign(['c'] * len(headers))
        table.header(headers)

        for match in matches:
            print(f'match: {match}: {result_map[match]}')
            data = [match]
            data.extend(value for value in result_map[match][0:])
            # print(f'Adding row: {data}')
            table.add_row(data)

        output = '```' + table.draw() + '```'
    else:
        table.set_cols_align(["l", "r"])
        table.set_cols_valign(["m", "m"])
        table.set_cols_width([10, 20])
        table.header([headers[0], matches[0]])
        data = list(zip(headers[1:], (result_map[matches[0]])[0:]))
        table.add_rows(data, header=False)
        output = '`' + table.draw() + '`'

    return output


def sort_stock(stock):
    # reverse = None (Sorts in Ascending order)
    # key is set to sort using third element of sublist
    return sorted(stock, key=lambda x: int(re.sub(r'\D+', '', x[2])))
