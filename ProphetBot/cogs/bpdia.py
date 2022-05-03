import re
import time
import timeit
from timeit import default_timer as timer

import discord
import discord.errors
import discord.utils
from discord import Embed, Member, Role, Color, CommandPermission
from discord.commands import Option, permissions
from discord.commands.context import ApplicationContext
from discord.ext import commands
from texttable import Texttable

from ProphetBot.bot import BpBot
from ProphetBot.helpers import *
from ProphetBot.models.embeds import ErrorEmbed, LogEmbed
from ProphetBot.models.sheets_objects import BuyEntry, SellEntry, GlobalEntry, CouncilEntry, MagewrightEntry, \
    ShopkeepEntry
from ProphetBot.models.sheets_objects import Character, BonusEntry, RpEntry, Faction, CharacterClass


def setup(bot):
    bot.add_cog(BPdia(bot))


def build_table(data):
    level = int(data['Level'])
    character_data = list()
    character_data.append(['Name', data['Name']])
    character_data.append(['Class', data['Class']])
    character_data.append(['Faction', data['Faction']])
    character_data.append(['Level', data['Level']])
    character_data.append(['Wealth', data['Total GP']])
    character_data.append(['Experience', data['Total XP']])

    if level >= 3:
        character_data.append(['Div GP', data['Div GP'] + '/' + data['GP Max']])
        character_data.append(['Div XP', data['Div XP'] + '/' + data['XP Max']])
        character_data.append(['ASL Mod', data['ASL Mod']])
    else:
        needed_arena = 1 if level == 1 else 2
        needed_rp = 1 if level == 1 else 2
        num_arena = int(data['L1 Arena']) if level == 1 else (int(data['L2 Arena 1/2']) + int(data['L2 Arena 2/2']))
        num_rp = int(data['L1 RP']) if level == 1 else (int(data['L2 RP 1/2']) + int(data['L2 RP 2/2']))
        character_data.append(['RP', str(num_rp) + '/' + str(needed_rp)])
        character_data.append(['Arena', str(num_arena) + '/' + str(needed_arena)])

    table = Texttable()
    table.set_cols_align(["l", "r"])
    table.set_cols_valign(["m", "m"])
    table.add_rows(character_data)
    return table.draw()


def build_get_embed(character: Character, player: Member) -> Embed:
    """
    Puts together a character information embed for the provided player's character

    :param character: Character we're pulling the information for
    :param player: Member of the character's player
    :return: Embed object fully formatted and ready to go
    """

    # Initial setup
    description = f"**Class:** {character.character_class}\n" \
                  f"**Faction:** {character.faction}\n" \
                  f"**Level:** {character.level}\n" \
                  f"**Experience:** {character.experience} xp\n" \
                  f"**Wealth:** {character.wealth} gp"
    faction_role = discord.utils.get(player.roles, name=character.faction)
    embed = Embed(
        title=f"Character Info - {character.name}",
        description=description,
        color=faction_role.color if faction_role else Color.dark_grey()
    )
    embed.set_thumbnail(url=player.display_avatar.url)

    # First add the weekly limits
    embed.add_field(name="Weekly Limits:",
                    value=f"\u200b \u200b \u200b Diversion GP: {character.div_gp}/{character.max_gp}\n"
                          f"\u200b \u200b \u200b Diversion XP: {character.div_xp}/{character.max_xp}",
                    inline=False)

    # Then we add some new player quest info for level 1 & 2s
    if character.level < 3:
        embed.add_field(name="First Steps Quests:",
                        value=f"\u200b \u200b \u200b Level {character.level} RPs: "
                              f"{character.completed_rps}/{character.needed_rps}\n"
                              f"\u200b \u200b \u200b Level {character.level} Arenas: "
                              f"{character.completed_arenas}/{character.needed_arenas}")

    return embed


def get_cl(char_xp):
    return 1 + int((int(char_xp) / 1000))


def get_faction_role(player: Member) -> Role:
    """
    Returns the first matching faction role of the provided player, or None if no faction roles are found

    :param player: A Member object representing the player in question
    :return: The first matching faction Role
    """
    faction_names = Faction.values_list()
    return discord.utils.find(lambda r: r.name in faction_names, player.roles)


class BPdia(commands.Cog):
    bot: BpBot  # Typing annotation for my IDE's sake

    def __init__(self, bot):
        # All GSheet endpoints are in the bot object now
        self.bot = bot
        print(f'Cog \'BPdia\' loaded')

    @commands.slash_command(
        name="create",
        description="Creates a new character",
        default_permission=False
    )
    @permissions.has_any_role("Magewright", "Council")
    async def create_character(
            self, ctx: ApplicationContext,
            player: Option(Member, "Character's player", required=True),
            name: Option(str, "Character's name", required=True),
            character_class: Option(str, "Character's (initial) class", choices=CharacterClass.option_list(),
                                    required=True),
            gp: Option(int, "Unspent starting gold", min=0, max=99999, required=True),
            level: Option(int, "Starting level for higher-level characters", min_value=1, max_value=20, default=1)
    ):
        start = time.time()
        print(f'Incoming \'Create\' command invoked by {ctx.author.name}. '
              f'Args: [ {player}, {name}, {character_class}, {gp}, {level} ]')

        # Everything is built off the assumption that each player only has one active character, so check for that
        if self.bot.sheets.get_character_from_id(player.id) is not None:
            print(f"Found existing character for {player.id}, aborting")
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"Player {player.mention} already has a character. Have a Council member "
                                             f"archive the old character before creating a new one."),
                ephemeral=True
            )
            return

        xp = (level - 1) * 1000  # Base XP for level 1 is 0 XP, 2 is 1000 XP, etc
        new_character = Character(player.id, name, CharacterClass(character_class), Faction.INITIATE, gp, xp)
        initial_log = BonusEntry(f"{ctx.author.name}#{ctx.author.discriminator}", new_character, "Initial Log", 0, 0)

        self.bot.sheets.create_character(new_character)
        self.bot.sheets.log_activity(initial_log)

        embed = Embed(title=f"Character Created - {name}",
                      description=f"**Player:** {player.mention}\n"
                                  f"**Class:** {character_class}\n"
                                  f"**Starting Gold:** {gp}\n"
                                  f"**Starting Level:** {level}",
                      color=discord.Color.random())
        embed.set_thumbnail(url=player.display_avatar.url)
        embed.set_footer(text=f"Created by: {ctx.author.name}#{ctx.author.discriminator}",
                         icon_url=ctx.author.display_avatar.url)

        await ctx.response.send_message(embed=embed)
        end = time.time()
        print(f"Time to create character: {end - start}s")

    @commands.slash_command(
        name="get",
        description="Displays character information for a player's character"
    )
    async def get_character(self, ctx: ApplicationContext,
                            player: Option(Member, "Player to get the information of", required=False)):
        if player is None:
            player = ctx.author
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return

        await ctx.response.send_message(embed=build_get_embed(character, player), ephemeral=False)

    @permissions.has_any_role("Magewright", "Council")
    @commands.slash_command(
        name="rp",
        description="Logs a completed RP",
        default_permission=False,
        permissions=[CommandPermission("Magewright", 1, True)]
    )
    async def log_rp(self, ctx: ApplicationContext,
                     player: Option(Member, description="Player who participated in the RP", required=True)):
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return

        log_entry = RpEntry(f"{ctx.author.name}#{ctx.author.discriminator}", character)
        self.bot.sheets.log_activity(log_entry)

        await ctx.response.send_message(embed=LogEmbed(ctx, log_entry), ephemeral=False)

    @permissions.has_any_role("Magewright", "Council")
    @commands.slash_command(
        name="bonus",
        description="Gives bonus GP and/or XP to a player",
        default_permission=False
    )
    async def log_bonus(self, ctx: ApplicationContext,
                        player: Option(Member, description="Player receiving the bonus", required=True),
                        reason: Option(str, description="The reason for the bonus", required=True),
                        gold: Option(int, description="The amount of gp", default=0, min=0, max=2000),
                        experience: Option(int, description="The amount of xp", default=0, min=0, max=150)):
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return

        log_entry = BonusEntry(f"{ctx.author.name}#{ctx.author.discriminator}", character, reason, gold, experience)
        self.bot.sheets.log_activity(log_entry)

        await ctx.response.send_message(embed=LogEmbed(ctx, log_entry), ephemeral=False)

    @commands.slash_command(
        name="buy",
        description="Logs the sale of an item to a player",
        default_permission=False
    )
    @permissions.has_any_role("Magewright", "Council")
    async def log_buy(self, ctx: ApplicationContext,
                      player: Option(Member, description="Player who bought the item", required=True),
                      item: Option(str, description="The item being bought", required=True),
                      cost: Option(int, description="The cost of the item", min=0, max=999999, required=True)):
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return
        if character.wealth < cost:
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"{player.mention} cannot afford the {cost}gp cost")
            )
            return

        log_entry = BuyEntry(f"{ctx.author.name}#{ctx.author.discriminator}", character, item, cost)
        self.bot.sheets.log_activity(log_entry)

        await ctx.response.send_message(embed=LogEmbed(ctx, log_entry), ephemeral=False)

    @commands.slash_command(
        name="sell",
        description="Logs the sale of an item from a player. Not for player establishment sales",
        default_permission=False,
    )
    @permissions.has_any_role("Magewright", "Council")
    async def log_sell(self, ctx: ApplicationContext,
                       player: Option(Member, description="Player who sold the item", required=True),
                       item: Option(str, description="The item being sold", required=True),
                       cost: Option(int, description="The amount of gp received for the sale",
                                    min=0, max=999999, required=True)):
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return

        log_entry = SellEntry(f"{ctx.author.name}#{ctx.author.discriminator}", character, item, cost)
        self.bot.sheets.log_activity(log_entry)

        await ctx.response.send_message(embed=LogEmbed(ctx, log_entry), ephemeral=False)

    @commands.slash_command(
        name="global",
        description="Logs a player's participation in a global",
        default_permission=False
    )
    @permissions.has_any_role("Magewright", "Council")
    async def log_global(self, ctx: ApplicationContext,
                         player: Option(Member, description="Player receiving the bonus", required=True),
                         global_name: Option(str, description="The name of the global activity", required=True),
                         gold: Option(int, description="The amount of gp", min=0, max=2000, required=True),
                         experience: Option(int, description="The amount of xp", min=0, max=150, required=True)):
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return

        log_entry = GlobalEntry(f"{ctx.author.name}#{ctx.author.discriminator}", character,
                                global_name, gold, experience)
        self.bot.sheets.log_activity(log_entry)

        await ctx.response.send_message(embed=LogEmbed(ctx, log_entry), ephemeral=False)

    @commands.slash_command(
        name="weekly",
        description="Performs the weekly reset",
        default_permission=False
    )
    @permissions.has_role("Council")
    async def weekly_reset(self, ctx: ApplicationContext):
        print(f"Weekly reset initiate by {ctx.author}")
        async with ctx.typing():  # Have the bot show as typing, as this may take a while

            # Process pending GP/XP
            start = timer()
            pending_gp_xp = self.bot.sheets.char_sheet.batch_get(['F3:F', 'I3:I', 'J1'])
            gp_total = list(pending_gp_xp[0])
            xp_total = list(pending_gp_xp[1])
            server_xp = list(pending_gp_xp[2])
            print(f'gp: {gp_total}\n'
                  f'xp: {xp_total}\n'
                  f'server_xp: {server_xp}')

            try:
                self.bot.sheets.char_sheet.batch_update([{
                    'range': 'E3:E',
                    'values': gp_total
                }, {
                    'range': 'H3:H',
                    'values': xp_total
                }, {
                    'range': 'F1',
                    'values': server_xp
                }])
            except gspread.exceptions.APIError as e:
                print(e)
                await ctx.response.send_message("Error: Trouble setting GP/XP values. Aborting.", ephemeral=True)
                return
            else:
                end = timer()
                print(f"Successfully copied GP and XP values in {end - start}s")

            # Archive old log entries
            start = timer()
            pending_logs = self.bot.sheets.log_sheet.get('A2:H')

            try:
                self.bot.sheets.log_archive.append_rows(pending_logs, value_input_option='USER_ENTERED',
                                                        insert_data_option='INSERT_ROWS', table_range='A2')
                self.bot.sheets.bpdia_workbook.values_clear('Log!A2:H')
            except gspread.exceptions.APIError:
                await ctx.response.send_message("Error: Trouble archiving log entries. Aborting.", ephemeral=True)
                return
            else:
                end = timer()
                print(f"Successfully archived old log entries in {end - start}s")

            # Finally, hand out weekly stipends
            start = timer()
            characters = self.bot.sheets.get_all_characters()
            council_role = discord.utils.get(ctx.guild.roles, name="Council")
            magewright_role = discord.utils.get(ctx.guild.roles, name="Magewright")
            shopkeep_role = discord.utils.get(ctx.guild.roles, name="Shopkeeper")
            council_ids = [m.id for m in council_role.members]

            council_characters = characters_by_ids(characters, council_ids)
            magewright_charcters = characters_by_ids(characters,
                                               [m.id for m in magewright_role.members if m not in council_ids])
            shopkeep_characters = characters_by_ids(characters, [m.id for m in shopkeep_role.members])

            log_entries = []
            log_entries.extend(
                [CouncilEntry(f"{self.bot.user.name}#{self.bot.user.discriminator}", c) for c in council_characters]
            )
            log_entries.extend(
                [MagewrightEntry(f"{self.bot.user.name}#{self.bot.user.discriminator}", c) for c in magewright_charcters]
            )
            log_entries.extend(
                [ShopkeepEntry(f"{self.bot.user.name}#{self.bot.user.discriminator}", c) for c in shopkeep_characters]
            )

            self.bot.sheets.log_activities(log_entries)
            end = timer()
            print(f"Successfully applied weekly stipends in {end - start}s")

            await ctx.response.send_message(f"Weekly reset complete")

    @commands.slash_command(
        name="faction",
        description="Sets the target player's faction"
    )
    async def set_faction(self, ctx: ApplicationContext,
                          player: Option(Member, description="Player joining the faction", required=True),
                          faction: Option(str, description="Faction to join", required=True,
                                          choices=Faction.option_list())):
        current_faction_role = get_faction_role(player)
        player: Member
        new_faction_role = discord.utils.get(ctx.guild.roles, name=faction)
        if new_faction_role is None:
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"Faction role with name {faction} could not be found"))
            return
        if current_faction_role is not None:
            await player.remove_roles(current_faction_role, reason=f"Joining new faction [ {faction} ]")

        try:
            self.bot.sheets.update_faction(player.id, faction)
        except ValueError:
            await ctx.response.send_message(embed=ErrorEmbed(
                description=f"Player {player.mention} not found in BPdia. You may need to `/create` then first."),
                ephemeral=True
            )
            return
        await player.add_roles(new_faction_role, reason=f"Joining new faction [ {faction} ]")
        embed = Embed(title="Success!",
                      description=f"{player.mention} has joined {faction}!",
                      color=new_faction_role.color)
        embed.set_thumbnail(url=player.display_avatar.url)

        await ctx.response.send_message(embed=embed)

    @commands.slash_command(
        name="level",
        description="Manually levels a character that has completed their Level 1 or Level 2 quests"
    )
    async def level_character(self, ctx: ApplicationContext,
                              player: Option(Member, description="Player receiving the level bump", required=True)):
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return
        if character.level > 2:
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"{player.mention} is already level {character.level}. "
                                             f"If they leveled the hard way then, well, congrats"),
                ephemeral=True
            )
            return
        if character.needed_rps != character.completed_rps or character.needed_arenas != character.completed_arenas:
            await ctx.response.send_message(
                embed=ErrorEmbed(description=f"{player.mention} has not completed their requirements to level up.\n"
                                             f"Completed RPs: {character.completed_rps}/{character.needed_rps}\n"
                                             f"Completed Arenas: {character.completed_arenas}/{character.needed_arenas}"),
                ephemeral=True
            )
            return

        new_xp = 1000 if character.level == 1 else 2000
        print(f"Setting reset_xp of character with id [ {character.player_id} ] to [ {new_xp} ]")
        self.bot.sheets.update_reset_xp(character.player_id, new_xp)

        embed = Embed(title="Level up successful!",
                      description=f"{player.mention} is now level {character.level + 1}",
                      color=Color.random())
        embed.set_thumbnail(url=player.display_avatar.url)

        await ctx.response.send_message(embed=embed)

    @commands.command(brief='- Provides a link to the public BPdia sheet')
    async def sheet(self, ctx):
        link = '<https://docs.google.com/spreadsheets/d/' + '1Ps6SWbnlshtJ33Yf30_1e0RkwXpaPy0YVFYaiETnbns' + '/>'
        await ctx.message.channel.send(f'The BPdia public sheet can be found at:\n{link}')
        await ctx.message.delete()

    @commands.command(brief='- Manually levels initiates',
                      help=LEVEL_HELP)
    @commands.has_any_role('Tracker', 'Magewright')
    async def level(self, ctx, disc_user):
        # TODO: This duplicates XP by adding non-reset XP to reset XP
        user_map = self.get_user_map()
        print(f'{str(datetime.utcnow())} - Incoming \'Level\' command from {ctx.message.author.name}'
              f'. Args: {disc_user}')

        target = re.sub(r'\D+', '', disc_user)
        if target not in user_map:
            await ctx.message.channel.send(NAME_ERROR)
            return

        if (targetXP := int(user_map[target])) > 2000:
            await ctx.message.channel.send('Error: The targeted player has over 2000 XP. Please enter manually.')
            return
        elif targetXP < 2000:
            new_xp = targetXP + 1000
        else:
            new_xp = 1000

        print(new_xp)
        index = list(user_map.keys()).index(target)  # Dicts preserve order in Python 3. Fancy.
        xp_range = 'H' + str(index + 3)  # Could find the index in this same line, but that's messy
        try:
            self.bot.sheets.char_sheet.update(xp_range, new_xp)
        except Exception as E:
            await ctx.message.channel.send(f'Error occurred while sending data to the sheet')
            print(f'level exception: {type(E)}')
            return
        await ctx.message.channel.send(f'{disc_user} - level submitted by {ctx.author.nick}')
        await ctx.message.delete()

    # --------------------------- #
    # Helper functions
    # --------------------------- #

    def get_user_map(self):
        USERLIST_RANGE = 'A3:A'
        XPLIST_RANGE = 'I3:I'
        try:
            results = self.bot.sheets.char_sheet.batch_get([USERLIST_RANGE, XPLIST_RANGE])
        except gspread.exceptions.APIError as E:
            print(E)

        return {  # Using fancy dictionary comprehension to make the dict
            str(key[0]): int(value[0]) for key, value in zip(results[0], results[1])
        }

    def get_character_from_id(self, discord_id: str) -> Character:
        header_row = '2:2'
        target_cell = self.bot.sheets.char_sheet.find(discord_id, in_column=1)
        user_row = str(target_cell.row) + ':' + str(target_cell.row)

        data = self.bot.sheets.char_sheet.batch_get([header_row, user_row])
        return Character(data)
