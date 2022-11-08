from timeit import default_timer as timer
from typing import List

import discord
from discord import SlashCommandGroup, Option, ApplicationContext, Member, Embed, Color
from discord.ext import commands
from ProphetBot.bot import BpBot
from ProphetBot.helpers import remove_fledgling_role, get_character_quests, get_character, get_player_character_class, \
    create_logs, get_faction_roles, get_level_cap, get_or_create_guild
from ProphetBot.helpers.autocomplete_helpers import *
from ProphetBot.models.db_objects import PlayerCharacter, PlayerCharacterClass, DBLog, Faction, LevelCaps, PlayerGuild
from ProphetBot.models.embeds import ErrorEmbed, NewCharacterEmbed, CharacterGetEmbed
from ProphetBot.models.schemas import CharacterSchema
from ProphetBot.queries import insert_new_character, insert_new_class, update_character

def setup(bot: commands.Bot):
    bot.add_cog(Character(bot))


class Character(commands.Cog):
    bot: BpBot
    character_commands = SlashCommandGroup("character", "Character commands")
    faction_commands = SlashCommandGroup("faction", "Faction commands")

    def __init__(self, bot):
        self.bot = bot
        print(f'Cog \'Characters\' loaded')

    @character_commands.command(
        name="create",
        description="Create a character"
    )
    async def character_create(self, ctx: ApplicationContext,
                               player: Option(Member, description="Character's player", required=True),
                               name: Option(str, description="Character's name", required=True),
                               character_class: Option(str, description="Character's initial class",
                                                       autocomplete=character_class_autocomplete,
                                                       required=True),
                               character_race: Option(str, description="Character's race",
                                                      autocomplete=character_race_autocomplete,
                                                      required=True),
                               gold: Option(int, description="Unspent starting gold", min=0, max=99999, required=True),
                               character_subrace: Option(str, description="Character's subrace",
                                                         autocomplete=character_subrace_autocomplete,
                                                         required=False),
                               character_subclass: Option(str, description="Character's subclass",
                                                          autocomplete=character_subclass_autocomplete,
                                                          required=False),
                               level: Option(int, description="Starting level for higher-level character", min_value=1,
                                             max_value=20, default=1)):
        start = timer()
        await ctx.defer()

        character: PlayerCharacter = await get_character(ctx.bot, player.id, ctx.guild_id)

        if character is not None:
            return await ctx.respond(f"Player {player.mention} already has a character. Have a council member"
                                     f"archive the old character before creating a new one.", ephemeral=True)

        # Resolve inputs
        c_class = ctx.bot.compendium.get_object("c_character_class", character_class)
        c_race = ctx.bot.compendium.get_object("c_character_race", character_race)
        c_subclass = ctx.bot.compendium.get_object("c_character_subclass", character_subclass)
        c_subrace = ctx.bot.compendium.get_object("c_character_subrace", character_subrace)
        init_faction = ctx.bot.compendium.get_object("c_faction", "Guild Initiate")

        # Create new object
        character = PlayerCharacter(player_id=player.id, guild_id=ctx.guild.id, name=name, race=c_race,
                                    subrace=c_subrace, xp=(level - 1) * 1000, div_xp=0, gold=gold, div_gold=0,
                                    active=True, reroll=False, faction=init_faction)

        async with self.bot.db.acquire() as conn:
            results = await conn.execute(insert_new_character(character))
            row = await results.first()

        if row is None:
            return await ctx.respond(f"Something went wrong", ephemeral=True)

        character: Character = CharacterSchema(ctx.bot.compendium).load(row)

        player_class = PlayerCharacterClass(character_id=character.id, primary_class=c_class,
                                            subclass=c_subclass, level=level, primary=True)

        async with self.bot.db.acquire() as conn:
            await conn.execute(insert_new_class(player_class))

        act = ctx.bot.compendium.get_object("c_activity", "BONUS")

        log_entry: DBLog = await create_logs(ctx, character, act, "Initial Log")

        await remove_fledgling_role(ctx, player, "Character created")
        end = timer()
        await ctx.respond(embed=NewCharacterEmbed(character, player, player_class, log_entry, ctx))
        print(f"Time to create character: {end - start:.2f}s")

    @character_commands.command(
        name="get",
        description="Displays character information for a player's character"
    )
    async def character_get(self, ctx: ApplicationContext,
                            player: Option(Member, description="Player to get the information of",
                                           required=False)):
        await ctx.defer()

        if player is None:
            player = ctx.author

        character: PlayerCharacter = await get_character(ctx.bot, player.id, ctx.guild_id)
        g: PlayerGuild = await get_or_create_guild(ctx.bot.db, ctx.guild_id)

        if character is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            return await ctx.respond(embed=ErrorEmbed(
                description=f"No character information found for {player.mention}"),
                ephemeral=True)

        class_ary: List[PlayerCharacterClass] = await get_player_character_class(ctx.bot, character.id)

        caps: LevelCaps = get_level_cap(character, g, ctx.bot.compendium)

        if character.get_level() < 3:
            character = await get_character_quests(ctx.bot, character)

        await ctx.respond(embed=CharacterGetEmbed(character, class_ary, caps, ctx))

    @character_commands.command(
        name="level",
        description="Manually levels a character that has completed their Level 1 or Level 2 quests"
    )
    async def character_level(self, ctx: ApplicationContext,
                              player: Option(Member, description="Player receiving the level bump", required=True)):
        await ctx.defer()

        character: PlayerCharacter = await get_character(ctx.bot, player.id, ctx.guild_id)

        if character is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            return await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True)

        if character.get_level() > 2:
            return await ctx.respond(embed=ErrorEmbed(description=
                                                      f"{player.mention} is already level {character.get_level()}. "
                                                      f"If they leveled the hard way then, well, congrats"),
                                     ephemeral=True)

        character = await get_character_quests(ctx.bot, character)

        if character.needed_rps > character.completed_rps or character.needed_arenas > character.completed_arenas:
            return await ctx.respond(embed=ErrorEmbed(
                description=f"{player.mention} has not completed their requirements to level up.\n"
                            f"Completed RPs: {character.completed_rps}/{character.needed_rps}\n"
                            f"Completed Arenas: {character.completed_arenas}/{character.needed_arenas}"),
                ephemeral=True)

        print(f"Leveling up character with player id [ {player.id} ]. New level: [ {character.get_level() + 1} ]")

        act = ctx.bot.compendium.get_object("c_activity", "BONUS")

        await create_logs(ctx, character, act, "New player level up", 0, 1000)

        embed = Embed(title="Level up successful!",
                      description=f"{player.mention} is now level {character.get_level()}",
                      color=Color.random())
        embed.set_thumbnail(url=player.display_avatar.url)

        await ctx.respond(embed=embed)

    @character_commands.command(
        name="race",
        description="Set a characters race/subrace"
    )
    async def character_race(self, ctx: ApplicationContext,
                             player: Option(Member, description="Player to set the race/subrace for", required=True),
                             character_race: Option(str, description="Character's race",
                                                    autocomplete=character_race_autocomplete,
                                                    required=True),
                             character_subrace: Option(str, description="Character's subrace",
                                                       autocomplete=character_subrace_autocomplete,
                                                       required=False)):

        await ctx.defer()

        character: PlayerCharacter = await get_character(ctx.bot, player.id, ctx.guild_id)

        if character is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            return await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True)

        c_race = ctx.bot.compendium.get_object("c_character_race", character_race)
        c_subrace = ctx.bot.compendium.get_object("c_character_subrace", character_subrace)

        character.race = c_race
        character.subrace = c_subrace

        async with ctx.bot.db.acquire() as conn:
            await conn.execute(update_character(character))

        embed = Embed(title="Update successful!",
                      description=f"{character.name} now is {character.get_formatted_race()}",
                      color=Color.random())
        embed.set_thumbnail(url=player.display_avatar.url)

        await ctx.respond(embed=embed)

    @faction_commands.command(
        name="set",
        description="Sets the target player's faction"
    )
    async def faction_set(self, ctx: ApplicationContext,
                          player: Option(Member, description="Player joining the faction", required=True),
                          faction: Option(str, autocomplete=faction_autocomplete, required=True)):
        await ctx.defer()

        current_faction_roles = get_faction_roles(ctx.bot.compendium, player)
        faction: Faction = ctx.bot.compendium.get_object("c_faction", faction)

        character: PlayerCharacter = await get_character(ctx.bot, player.id, ctx.guild_id)

        if character is None:
            return await ctx.respond(embed=ErrorEmbed(f"No character information found for {player.mention}"),
                                     ephemeral=True)
        elif not (new_faction_role := discord.utils.get(ctx.guild.roles, name=faction.value)):
            return await ctx.respond(embed=ErrorEmbed(description=f"Faction role with name {faction.value}"
                                                                  f" could not be found"))

        if current_faction_roles is not None:
            await player.remove_roles(*current_faction_roles, reason=f"Joining new faction[ {faction.value} ]")

        character.faction = faction
        await player.add_roles(new_faction_role, reason=f"Joining new faction [ {faction.value} ]")

        async with ctx.bot.db.acquire() as conn:
            await conn.execute(update_character(character))

        await remove_fledgling_role(ctx, player, "Faction Updated")

        embed = Embed(title="Success!",
                      description=f"{player.mention} has joined {faction.value}!",
                      color=new_faction_role.color)
        embed.set_thumbnail(url=player.display_avatar.url)

        await ctx.respond(embed=embed)
