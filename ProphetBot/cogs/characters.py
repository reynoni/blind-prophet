import logging
from timeit import default_timer as timer
from typing import List

from discord import SlashCommandGroup, Option, ApplicationContext, Member, Embed, Color
from discord.ext import commands
from ProphetBot.bot import BpBot
from ProphetBot.helpers import remove_fledgling_role, get_character_quests, get_character, get_player_character_class, \
    create_logs, get_faction_roles, get_level_cap, get_or_create_guild, confirm, is_admin
from ProphetBot.helpers.autocomplete_helpers import *
from ProphetBot.models.db_objects import PlayerCharacter, PlayerCharacterClass, DBLog, Faction, LevelCaps, PlayerGuild
from ProphetBot.models.embeds import ErrorEmbed, NewCharacterEmbed, CharacterGetEmbed
from ProphetBot.models.schemas import CharacterSchema
from ProphetBot.queries import insert_new_character, insert_new_class, update_character, update_class

log = logging.getLogger(__name__)


def setup(bot: commands.Bot):
    bot.add_cog(Character(bot))


class Character(commands.Cog):
    bot: BpBot
    character_admin_commands = SlashCommandGroup("character_admin", "Character administration commands")
    faction_commands = SlashCommandGroup("faction", "Faction commands")

    def __init__(self, bot):
        self.bot = bot
        log.info(f'Cog \'Characters\' loaded')

    @character_admin_commands.command(
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
        """
        Creates a new character for a player

        :param ctx: Context
        :param player: Member
        :param name: Name of the PlayerCharacter
        :param character_class: CharacterClass
        :param character_race: CharacterRace
        :param gold: Starting gold
        :param character_subrace: CharacterSubrace
        :param character_subclass: CharacterSubclass
        :param level: Starting level if starting higher than 1
        """
        start = timer()
        await ctx.defer()

        character: PlayerCharacter = await get_character(ctx.bot, player.id, ctx.guild_id)

        if character is not None:
            return await ctx.respond(embed=ErrorEmbed(description=f"Player {player.mention} already has a character. "
                                                                  f"Have a council member archive the old character "
                                                                  f"before creating a new one."), ephemeral=True)

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
            log.error(f"CHARACTERS: Error writing character to DB for {ctx.guild.name} [ {ctx.guild_id} ]")
            return await ctx.respond(embed=ErrorEmbed(
                description=f"Something went wrong creating the character."),
                ephemeral=True)

        character: Character = CharacterSchema(ctx.bot.compendium).load(row)

        player_class = PlayerCharacterClass(character_id=character.id, primary_class=c_class,
                                            subclass=c_subclass, active=True)

        async with self.bot.db.acquire() as conn:
            await conn.execute(insert_new_class(player_class))

        act = ctx.bot.compendium.get_object("c_activity", "BONUS")

        log_entry: DBLog = await create_logs(ctx, character, act, "Initial Log")

        await remove_fledgling_role(ctx, player, "Character created")
        end = timer()
        log.info(f"Time to create character: [ {end - start:.2f} ]s")
        return await ctx.respond(embed=NewCharacterEmbed(character, player, player_class, log_entry, ctx))

    @commands.slash_command(
        name="get",
        description="Displays character information for a player's character"
    )
    async def character_get(self, ctx: ApplicationContext,
                            player: Option(Member, description="Player to get the information of",
                                           required=False)):
        """
        Gets and creates an embed of character information

        :param ctx: Context
        :param player: Member
        """
        await ctx.defer()

        if player is None:
            player = ctx.author

        character: PlayerCharacter = await get_character(ctx.bot, player.id, ctx.guild_id)
        g: PlayerGuild = await get_or_create_guild(ctx.bot.db, ctx.guild_id)

        if character is None:
            return await ctx.respond(embed=ErrorEmbed(
                description=f"No character information found for {player.mention}"),
                ephemeral=True)

        class_ary: List[PlayerCharacterClass] = await get_player_character_class(ctx.bot, character.id)

        caps: LevelCaps = get_level_cap(character, g, ctx.bot.compendium)

        if character.get_level() < 3:
            character = await get_character_quests(ctx.bot, character)

        await ctx.respond(embed=CharacterGetEmbed(character, class_ary, caps, ctx))

    @character_admin_commands.command(
        name="level",
        description="Manually levels a character that has completed their Level 1 or Level 2 quests"
    )
    async def character_level(self, ctx: ApplicationContext,
                              player: Option(Member, description="Player receiving the level bump", required=True)):
        """
        Manually levels a character once they've completed entry quests

        :param ctx: Context
        :param player: Member
        """

        await ctx.defer()

        character: PlayerCharacter = await get_character(ctx.bot, player.id, ctx.guild_id)

        if character is None:
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

        log.info(f"Leveling up character [ {character.id} ] with player id [ {player.id} ]. "
                 f"New level: [ {character.get_level() + 1} ]")

        act = ctx.bot.compendium.get_object("c_activity", "BONUS")

        await create_logs(ctx, character, act, "New player level up", 0, 1000)

        embed = Embed(title="Level up successful!",
                      description=f"{player.mention} is now level {character.get_level()}",
                      color=Color.random())
        embed.set_thumbnail(url=player.display_avatar.url)

        await ctx.respond(embed=embed)

    @character_admin_commands.command(
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
        """
        Sets a characters race/subrace

        :param ctx: Context
        :param player: Member
        :param character_race: CharacterRace
        :param character_subrace: CharacterSubrace
        """

        await ctx.defer()

        character: PlayerCharacter = await get_character(ctx.bot, player.id, ctx.guild_id)

        if character is None:
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
                      description=f"{character.name}'s race/subrace updated to {character.get_formatted_race()}",
                      color=Color.random())
        embed.set_thumbnail(url=player.display_avatar.url)

        await ctx.respond(embed=embed)

    @character_admin_commands.command(
        name="subclass",
        description="Sets the subclass for a given player and class"
    )
    async def character_subclass(self, ctx: ApplicationContext,
                                 player: Option(Member, description="Player to set the race/subrace for",
                                                required=True),
                                 character_class: Option(str, description="Character's class to modify",
                                                         autocomplete=character_class_autocomplete,
                                                         required=True),
                                 character_subclass: Option(str, description="Character's subclass",
                                                            autocomplete=character_subclass_autocomplete,
                                                            required=False)):
        """
        Given a player and class, will update the subclass

        :param ctx: Context
        :param player: Member
        :param character_class: CharacterClass
        :param character_subclass: CharacterSubclass
        """
        await ctx.defer()

        character: PlayerCharacter = await get_character(ctx.bot, player.id, ctx.guild_id)

        if character is None:
            return await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True)

        c_class = ctx.bot.compendium.get_object("c_character_class", character_class)
        c_subclass = ctx.bot.compendium.get_object("c_character_subclass", character_subclass)

        class_ary: List[PlayerCharacterClass] = await get_player_character_class(ctx.bot, character.id)

        for c in class_ary:
            if c.primary_class.id == c_class.id:
                c.subclass = c_subclass

                async with ctx.bot.db.acquire() as conn:
                    await conn.execute(update_class(c))

                embed = Embed(title="Update successful!",
                              description=f"{character.name} is class(es) updated to",
                              color=Color.random())
                embed.description += f"\n".join([f" {c.get_formatted_class()}" for c in class_ary])
                embed.set_thumbnail(url=player.display_avatar.url)

                return await ctx.respond(embed=embed)

        await ctx.respond(embed=ErrorEmbed(description=f"{character.name} doesn't have a {c_class.value} class"))

    @character_admin_commands.command(
        name="add_multiclass",
        description="Adds a multiclass to a player"
    )
    async def character_multiclass_add(self, ctx: ApplicationContext,
                                       player: Option(Member, description="Player to set the race/subrace for",
                                                      required=True),
                                       character_class: Option(str, description="Character's class to modify",
                                                               autocomplete=character_class_autocomplete,
                                                               required=True),
                                       character_subclass: Option(str, description="Character's subclass",
                                                                  autocomplete=character_subclass_autocomplete,
                                                                  required=False)):
        """
        Adds a new class to a player

        :param ctx: Context
        :param player: Member
        :param character_class: CharacterClass
        :param character_subclass: CharacterSubclass
        """
        await ctx.defer()

        character: PlayerCharacter = await get_character(ctx.bot, player.id, ctx.guild_id)

        if character is None:
            return await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True)

        c_class = ctx.bot.compendium.get_object("c_character_class", character_class)
        c_subclass = ctx.bot.compendium.get_object("c_character_subclass", character_subclass)

        class_ary: List[PlayerCharacterClass] = await get_player_character_class(ctx.bot, character.id)

        if c_class.id in list(c.primary_class.id for c in class_ary):
            return await ctx.respond(
                embed=ErrorEmbed(description=f"Character already has class {c_class.value}"),
                ephemeral=True)
        elif len(class_ary) + 1 > character.get_level():
            return await ctx.respond(
                embed=ErrorEmbed(description=f"Can't add more classes than the player has levels"),
                ephemeral=True)
        else:
            new_class = PlayerCharacterClass(character_id=character.id, primary_class=c_class, subclass=c_subclass,
                                             active=True)

            async with ctx.bot.db.acquire() as conn:
                await conn.execute(insert_new_class(new_class))

            class_ary.append(new_class)

            embed = Embed(title="Update successful!",
                          description=f"{character.name} classes updated to",
                          color=Color.random())
            embed.description += f"\n".join([f" {c.get_formatted_class()}" for c in class_ary])
            embed.set_thumbnail(url=player.display_avatar.url)

            return await ctx.respond(embed=embed)

    @character_admin_commands.command(
        name="remove_multiclass",
        description="Removes a class from a player"
    )
    async def character_multiclass_remove(self, ctx: ApplicationContext,
                                          player: Option(Member, description="Player to set the race/subrace for",
                                                         required=True),
                                          character_class: Option(str, description="Character's class to modify",
                                                                  autocomplete=character_class_autocomplete,
                                                                  required=True)):
        """
        Removes a multiclass from a player

        :param ctx: Context
        :param player: Member
        :param character_class: CharacterClass
        """
        await ctx.defer()

        character: PlayerCharacter = await get_character(ctx.bot, player.id, ctx.guild_id)

        if character is None:
            return await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True)

        c_class = ctx.bot.compendium.get_object("c_character_class", character_class)

        class_ary: List[PlayerCharacterClass] = await get_player_character_class(ctx.bot, character.id)

        if len(class_ary) == 1:
            return await ctx.respond(
                embed=ErrorEmbed(description=f"Character only has one class."),
                ephemeral=True)
        elif c_class.id not in list(c.primary_class.id for c in class_ary):
            return await ctx.respond(
                embed=ErrorEmbed(description=f"Character doesn't have class {c_class.value}"),
                ephemeral=True)
        else:
            for i in range(1, len(class_ary)):
                char_class = class_ary[i]

                if char_class.primary_class.id == c_class.id:
                    char_class.active = False
                    class_ary.remove(char_class)
                    async with ctx.bot.db.acquire() as conn:
                        await conn.execute(update_class(char_class))

            embed = Embed(title="Update successful!",
                          description=f"{character.name} classes updated to",
                          color=Color.random())
            embed.description += f"\n".join([f" {c.get_formatted_class()}" for c in class_ary])
            embed.set_thumbnail(url=player.display_avatar.url)

            return await ctx.respond(embed=embed)

    @character_admin_commands.command(
        name="inactivate",
        description="Marks a character as inactive on the server."
    )
    @commands.check(is_admin)
    async def character_inactivate(self, ctx: ApplicationContext,
                                   player: Option(Member, description="Player to inactivate character for.",
                                                  required=True)):
        await ctx.defer()

        character: PlayerCharacter = await get_character(ctx.bot, player.id, ctx.guild_id)

        if character is None:
            return await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True)

        conf = await confirm(ctx, f"Are you sure you want to inactivate `{character.name}` for {player.mention}? "
                                  f"(Reply with yes/no)", True)

        if conf is None:
            return await ctx.respond(f'Timed out waiting for a response or invalid response.', delete_after=10)
        elif not conf:
            return await ctx.respond(f'Ok, cancelling.', delete_after=10)

        character.active = False

        async with ctx.bot.db.acquire() as conn:
            await conn.execute(update_character(character))

        await ctx.respond(f"Character inactivated")

    @faction_commands.command(
        name="set",
        description="Sets the target player's faction"
    )
    async def faction_set(self, ctx: ApplicationContext,
                          player: Option(Member, description="Player joining the faction", required=True),
                          faction: Option(str, autocomplete=faction_autocomplete, required=True)):
        """
        Updates a player's faction

        :param ctx: Context
        :param player: Member
        :param faction: Faction
        """
        await ctx.defer()

        current_faction_roles = get_faction_roles(ctx.bot.compendium, player)
        faction: Faction = ctx.bot.compendium.get_object("c_faction", faction)

        character: PlayerCharacter = await get_character(ctx.bot, player.id, ctx.guild_id)

        if character is None:
            return await ctx.respond(embed=ErrorEmbed(f"No character information found for {player.mention}"),
                                     ephemeral=True)
        elif faction is None:
            if current_faction_roles is None:
                return await ctx.respond(embed=ErrorEmbed(description=f"Player already doesn't belong to a faction."))

            await player.remove_roles(*current_faction_roles, reason=f"Leaving faction")
            embed = Embed(title="Success!",
                          description=f"{player.mention} has left their faction!",
                          color=Color.random())
            embed.set_thumbnail(url=player.display_avatar.url)
            return await ctx.respond(embed=embed, ephemeral=True)
        elif not (new_faction_role := discord.utils.get(ctx.guild.roles, name=faction.value)):
            return await ctx.respond(embed=ErrorEmbed(description=f"Faction role with name {faction.value}"
                                                                  f" could not be found"),
                                     ephemeral=True)

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
