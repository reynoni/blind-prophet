import asyncio
import time
from timeit import default_timer as timer
from typing import List

import discord
import discord.errors
import discord.utils
import gspread
import psycopg2
from discord import Embed, Member, Role, Color, InteractionMessage, TextChannel
from discord.commands import Option
from discord.commands.context import ApplicationContext
from discord.ext import commands, tasks
from discord.ext.commands import Context
from gspread import GSpreadException
from marshmallow import ValidationError

from ProphetBot.bot import BpBot
from ProphetBot.helpers import filter_characters_by_ids
from ProphetBot.models.db_objects import RpDashboard
from ProphetBot.models.embeds import ErrorEmbed, LogEmbed, AdventureRewardEmbed, RpDashboardEmbed
from ProphetBot.models.schemas import AdventureSchema, RpDashboardSchema
from ProphetBot.models.sheets_objects import BuyEntry, SellEntry, GlobalEntry, CouncilEntry, MagewrightEntry, \
    ShopkeepEntry, Adventure, CampaignEntry
from ProphetBot.models.sheets_objects import Character, BonusEntry, RpEntry, Faction, CharacterClass
from ProphetBot.queries import get_dashboard_by_categorychannel_id, insert_new_dashboard, get_all_dashboards


def setup(bot):
    bot.add_cog(BPdia(bot))


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


def get_faction_role(player: Member) -> List[Role] | None:
    """
    Returns the first matching faction role of the provided player, or None if no faction roles are found

    :param player: A Member object representing the player in question
    :return: The first matching faction Role
    """
    faction_names = Faction.values_list()
    faction_names.remove(Faction.INITIATE.value)
    faction_names.remove(Faction.GUILD_MEMBER.value)
    roles = list(filter(lambda r: r.name in faction_names, player.roles))
    if len(roles) == 0:
        return None
    return roles


async def get_last_message(channel: TextChannel) -> discord.Message | None:
    last_message = channel.last_message
    if last_message is None:
        try:
            lm_id = channel.last_message_id
            last_message = await channel.fetch_message(lm_id) if lm_id is not None else None
        except discord.errors.HTTPException as e:
            print(f"Skipping channel {channel.name}: [ {e} ]")
            return None
    return last_message


class BPdia(commands.Cog):
    bot: BpBot  # Typing annotation for my IDE's sake

    def __init__(self, bot):
        # All GSheet endpoints are in the bot object now
        self.bot = bot
        print(f'Cog \'BPdia\' loaded')

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(3.0)
        await self.update_rp_dashboards.start()

    @commands.slash_command(
        name="create",
        description="Creates a new character"
    )
    async def create_character(
            self, ctx: ApplicationContext,
            player: Option(Member, "Character's player", required=True),
            name: Option(str, "Character's name", required=True),
            character_class: Option(str, "Character's (initial) class", choices=CharacterClass.optionchoice_list(),
                                    required=True),
            gp: Option(int, "Unspent starting gold", min=0, max=99999, required=True),
            level: Option(int, "Starting level for higher-level characters", min_value=1, max_value=20, default=1)
    ):
        start = time.time()
        await ctx.defer()  # Have the bot show as typing, as this may take a while

        print(f'\'Create\' command invoked by {ctx.author.name}. '
              f'Args: [ {player}, {name}, {character_class}, {gp}, {level} ]')

        # Everything is built off the assumption that each player only has one active character, so check for that
        if self.bot.sheets.get_character_from_id(player.id) is not None:
            print(f"Found existing character for {player.id}, aborting")
            await ctx.respond(
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

        await ctx.respond(embed=embed)
        end = time.time()
        print(f"Time to create character: {end - start}s")

    @commands.slash_command(
        name="get",
        description="Displays character information for a player's character"
    )
    async def get_character(self, ctx: ApplicationContext,
                            player: Option(Member, "Player to get the information of", required=False)):
        await ctx.defer()
        if player is None:
            player = ctx.author
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return

        await ctx.respond(embed=build_get_embed(character, player), ephemeral=False)

    @commands.slash_command(
        name="rp",
        description="Logs a completed RP",
    )
    async def log_rp(self, ctx: ApplicationContext,
                     player: Option(Member, description="Player who participated in the RP", required=True)):
        await ctx.defer()
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return

        log_entry = RpEntry(f"{ctx.author.name}#{ctx.author.discriminator}", character)
        self.bot.sheets.log_activity(log_entry)

        await ctx.respond(embed=LogEmbed(ctx, log_entry), ephemeral=False)

    @commands.slash_command(
        name="bonus",
        description="Gives bonus GP and/or XP to a player"
    )
    async def log_bonus(self, ctx: ApplicationContext,
                        player: Option(Member, description="Player receiving the bonus", required=True),
                        reason: Option(str, description="The reason for the bonus", required=True),
                        gold: Option(int, description="The amount of gp", default=0, min=0, max=2000),
                        experience: Option(int, description="The amount of xp", default=0, min=0, max=150)):
        await ctx.defer()
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return

        log_entry = BonusEntry(f"{ctx.author.name}#{ctx.author.discriminator}", character, reason, gold, experience)
        self.bot.sheets.log_activity(log_entry)

        await ctx.respond(embed=LogEmbed(ctx, log_entry), ephemeral=False)

    @commands.slash_command(
        name="buy",
        description="Logs the sale of an item to a player"
    )
    async def log_buy(self, ctx: ApplicationContext,
                      player: Option(Member, description="Player who bought the item", required=True),
                      item: Option(str, description="The item being bought", required=True),
                      cost: Option(int, description="The cost of the item", min=0, max=999999, required=True)):
        await ctx.defer()
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return
        if character.wealth < cost:
            await ctx.respond(embed=ErrorEmbed(description=f"{player.mention} cannot afford the {cost}gp cost"))
            return

        log_entry = BuyEntry(f"{ctx.author.name}#{ctx.author.discriminator}", character, item, cost)
        self.bot.sheets.log_activity(log_entry)

        await ctx.respond(embed=LogEmbed(ctx, log_entry), ephemeral=False)

    @commands.slash_command(
        name="sell",
        description="Logs the sale of an item from a player. Not for player establishment sales"
    )
    async def log_sell(self, ctx: ApplicationContext,
                       player: Option(Member, description="Player who sold the item", required=True),
                       item: Option(str, description="The item being sold", required=True),
                       cost: Option(int, description="The amount of gp received for the sale",
                                    min=0, max=999999, required=True)):
        await ctx.defer()
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return

        log_entry = SellEntry(f"{ctx.author.name}#{ctx.author.discriminator}", character, item, cost)
        self.bot.sheets.log_activity(log_entry)

        await ctx.respond(embed=LogEmbed(ctx, log_entry), ephemeral=False)

    @commands.slash_command(
        name="global",
        description="Logs a player's participation in a global"
    )
    async def log_global(self, ctx: ApplicationContext,
                         player: Option(Member, description="Player receiving the bonus", required=True),
                         global_name: Option(str, description="The name of the global activity", required=True),
                         gold: Option(int, description="The amount of gp", min=0, max=2000, required=True),
                         experience: Option(int, description="The amount of xp", min=0, max=150, required=True)):
        await ctx.defer()
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return

        log_entry = GlobalEntry(f"{ctx.author.name}#{ctx.author.discriminator}", character,
                                global_name, gold, experience)
        self.bot.sheets.log_activity(log_entry)

        await ctx.respond(embed=LogEmbed(ctx, log_entry), ephemeral=False)

    @commands.slash_command(
        name="ep",
        description="Grants adventure rewards to the specified adventure"
    )
    async def log_adventure(self, ctx: ApplicationContext,
                            role: Option(Role, description="The adventure role to get rewards", required=True),
                            ep: Option(int, description="The number of EP to give rewards for", required=True)):
        await ctx.defer()
        try:
            adventure_raw = self.bot.sheets.get_adventure_from_role_id(role.id)
            if adventure_raw is None:
                await ctx.respond(
                    embed=ErrorEmbed(description=f"No adventure found for {role.mention}"),
                    ephemeral=True
                )
                return
            adventure: Adventure = AdventureSchema().load(adventure_raw)
        except ValidationError:
            await ctx.respond(
                embed=ErrorEmbed(description=f"Unable to validate adventure data for {role.mention}"),
                ephemeral=True
            )
            return
        except GSpreadException:
            await ctx.respond(
                embed=ErrorEmbed(description=f"Error getting adventure information from BPdia"),
                ephemeral=True
            )
            return

        all_characters = self.bot.sheets.get_all_characters()
        dm_characters = adventure.get_dm_characters(all_characters)
        player_characters = adventure.get_player_characters(ctx, all_characters)

        log_entries = []
        for dm in dm_characters:
            log_entries.append(CampaignEntry(ctx.author, dm, adventure.name, ep, True))
        for player in player_characters:
            log_entries.append(CampaignEntry(ctx.author, player, adventure.name, ep, False))

        if len(log_entries) == 0:
            await ctx.respond(
                embed=ErrorEmbed(description=f"Role {role} has no members. Aborting"),
                ephemeral=True
            )
            return

        self.bot.sheets.log_activities(log_entries)

        reward_embed = AdventureRewardEmbed(ctx, dm_characters, player_characters, adventure, ep)
        await ctx.respond(embed=reward_embed, ephemeral=False)

    @commands.slash_command(
        name="weekly",
        description="Performs the weekly reset"
    )
    async def weekly_reset(self, ctx: ApplicationContext):
        print(f"Weekly reset initiate by {ctx.author}")
        await ctx.defer()  # Have the bot show as typing, as this may take a while

        # Process pending GP/XP
        start = timer()
        pending_gp_xp = self.bot.sheets.char_sheet.batch_get(['F3:F', 'I3:I', 'J1'])
        gp_total = [[int(g[0])] for g in list(pending_gp_xp[0])]  # Cast all the numerical values into ints
        xp_total = [[int(x[0])] for x in list(pending_gp_xp[1])]  # Google returns them as strings for some reason
        server_xp = [[int(s[0])] for s in list(pending_gp_xp[2])]  # Ugly, but it works
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
            await ctx.respond("Error: Trouble setting GP/XP values. Aborting.", ephemeral=True)
            return
        else:
            gp_xp_end = timer()
            print(f"Successfully copied GP and XP values in {gp_xp_end - start}s")

        # Archive old log entries
        pending_logs = self.bot.sheets.log_sheet.get('A2:H')

        try:
            self.bot.sheets.log_archive.append_rows(pending_logs, value_input_option='USER_ENTERED',
                                                    insert_data_option='INSERT_ROWS', table_range='A2')
            self.bot.sheets.bpdia_workbook.values_clear('Log!A2:H')
        except gspread.exceptions.APIError:
            await ctx.respond("Error: Trouble archiving log entries. Aborting.", ephemeral=True)
            return
        else:
            logs_end = timer()
            print(f"Successfully archived old log entries in {logs_end - gp_xp_end}s")

        # Finally, hand out weekly stipends
        characters = self.bot.sheets.get_all_characters()
        council_role = discord.utils.get(ctx.guild.roles, name="Council")
        magewright_role = discord.utils.get(ctx.guild.roles, name="Magewright")
        shopkeep_role = discord.utils.get(ctx.guild.roles, name="Shopkeeper")
        council_ids = [m.id for m in council_role.members]

        council_characters = filter_characters_by_ids(characters, council_ids)
        magewright_charcters = filter_characters_by_ids(characters,
                                                        [m.id for m in magewright_role.members if m.id not in council_ids])
        shopkeep_characters = filter_characters_by_ids(characters, [m.id for m in shopkeep_role.members])

        log_entries = []
        if council_characters:
            log_entries.extend(
                [CouncilEntry(f"{self.bot.user.name}#{self.bot.user.discriminator}", c) for c in council_characters]
            )
        if magewright_charcters:
            log_entries.extend(
                [MagewrightEntry(f"{self.bot.user.name}#{self.bot.user.discriminator}", c) for c in
                 magewright_charcters]
            )
        if shopkeep_characters:
            log_entries.extend(
                [ShopkeepEntry(f"{self.bot.user.name}#{self.bot.user.discriminator}", c) for c in shopkeep_characters]
            )

        self.bot.sheets.log_activities(log_entries)
        end = timer()
        print(f"Successfully applied weekly stipends in {end - logs_end}s")

        await ctx.respond(f"Weekly reset complete in {end - start:.2f} seconds")

    @commands.slash_command(
        name="faction",
        description="Sets the target player's faction"
    )
    async def set_faction(self, ctx: ApplicationContext,
                          player: Option(Member, description="Player joining the faction", required=True),
                          faction: Option(str, description="Faction to join", required=True,
                                          choices=Faction.optionchoice_list())):
        await ctx.defer()
        current_faction_roles = get_faction_role(player)
        new_faction_role = discord.utils.get(ctx.guild.roles, name=faction)
        if new_faction_role is None:
            await ctx.respond(
                embed=ErrorEmbed(description=f"Faction role with name {faction} could not be found"))
            return

        if current_faction_roles is not None:
            await player.remove_roles(*current_faction_roles, reason=f"Joining new faction [ {faction} ]")

        try:
            self.bot.sheets.update_faction(player.id, faction)
        except ValueError:
            await ctx.respond(embed=ErrorEmbed(
                description=f"Player {player.mention} not found in BPdia. You may need to `/create` then first."),
                ephemeral=True
            )
            return
        await player.add_roles(new_faction_role, reason=f"Joining new faction [ {faction} ]")
        embed = Embed(title="Success!",
                      description=f"{player.mention} has joined {faction}!",
                      color=new_faction_role.color)
        embed.set_thumbnail(url=player.display_avatar.url)

        await ctx.respond(embed=embed)

    @commands.slash_command(
        name="level",
        description="Manually levels a character that has completed their Level 1 or Level 2 quests"
    )
    async def level_character(self, ctx: ApplicationContext,
                              player: Option(Member, description="Player receiving the level bump", required=True)):
        await ctx.defer()
        if (character := self.bot.sheets.get_character_from_id(player.id)) is None:
            print(f"No character information found for player [ {player.id} ], aborting")
            await ctx.respond(
                embed=ErrorEmbed(description=f"No character information found for {player.mention}"),
                ephemeral=True
            )
            return
        if character.level > 2:
            await ctx.respond(
                embed=ErrorEmbed(description=f"{player.mention} is already level {character.level}. "
                                             f"If they leveled the hard way then, well, congrats"),
                ephemeral=True
            )
            return
        if character.needed_rps != character.completed_rps or character.needed_arenas != character.completed_arenas:
            await ctx.respond(
                embed=ErrorEmbed(
                    description=f"{player.mention} has not completed their requirements to level up.\n"
                                f"Completed RPs: {character.completed_rps}/{character.needed_rps}\n"
                                f"Completed Arenas: {character.completed_arenas}/{character.needed_arenas}"),
                ephemeral=True
            )
            return

        print(f"Leveling up character with player id [ {player.id} ]. New level: [ {character.level + 1} ]")
        self.bot.sheets.log_activity(
            BonusEntry(f"{ctx.author.name}#{ctx.author.discriminator}", character, "New player level up", 0, 1000)
        )

        embed = Embed(title="Level up successful!",
                      description=f"{player.mention} is now level {character.level + 1}",
                      color=Color.random())
        embed.set_thumbnail(url=player.display_avatar.url)

        await ctx.respond(embed=embed)

    @commands.slash_command(
        name="create_dashboard",
        description="Creates a dashboard which shows the status of RP channels in this category"
    )
    async def rp_dashboard_create(
            self, ctx: ApplicationContext,
            excluded_channel_1: Option(TextChannel, "The first channel to exclude", required=False, default=None),
            excluded_channel_2: Option(TextChannel, "The second channel to exclude", required=False, default=None),
            excluded_channel_3: Option(TextChannel, "The third channel to exclude", required=False, default=None),
            excluded_channel_4: Option(TextChannel, "The fourth channel to exclude", required=False, default=None),
            excluded_channel_5: Option(TextChannel, "The fifth channel to exclude", required=False, default=None)
    ):
        # Check to see whether a dashboard already exists in this category
        async with self.bot.db.acquire() as conn:
            results = await conn.execute(get_dashboard_by_categorychannel_id(ctx.channel.category_id))
            dashboard_row = await results.first()
        if dashboard_row is not None:
            await ctx.respond(embed=ErrorEmbed(description="There is already a dashboard for this category. "
                                                           "Delete that before creating another"))
            return
        # Process excluded channels
        excluded_channels = list(set(filter(
            lambda c: c is not None,
            [excluded_channel_1, excluded_channel_2, excluded_channel_3, excluded_channel_4, excluded_channel_5]
        )))
        # Create post with dummy text and pin it
        interaction = await ctx.respond("Fetching dashboard data. This may take a moment...")
        msg: InteractionMessage = await interaction.original_message()
        await msg.pin(reason=f"RP dashboard for {ctx.channel.category.name} created by {ctx.author.name}")
        # Write new row to database
        try:
            async with self.bot.db.acquire() as conn:
                await conn.execute(insert_new_dashboard(
                    category_id=ctx.channel.category.id,
                    post_channel_id=ctx.channel_id,
                    post_id=msg.id,
                    excluded_channels=[c.id for c in excluded_channels]
                ))
        # Delete post if we catch an error
        except psycopg2.Error:
            await msg.delete()
            await ctx.respond(ErrorEmbed(description="A database error was encountered. Aborting."))
            return
        #   Otherwise give an extra success post
        else:
            print("RP dashboard created")
            # Manually call update dashboards task
            await self.update_rp_dashboards()

    @staticmethod
    async def cog_before_invoke(ctx: Context):  # Log commands being run to better tie them to errors
        print(f"Command [ /{ctx.command.qualified_name} ] initiated by member "
              f"[ {ctx.author.name}#{ctx.author.discriminator}, id: {ctx.author.id} ]")

    async def update_dashboard(self, dashboard: RpDashboard):
        channels = dashboard.channels_to_check(self.bot)
        channels_dict = {
            "Magewright": [],
            "Available": [],
            "In Use": []
        }
        guild = dashboard.get_categorychannel(self.bot).guild
        magewright_role = discord.utils.get(guild.roles, name="Magewright")
        for channel in channels:
            last_message = await get_last_message(channel)

            if last_message is None or last_message.content == "```\n \n```":
                channels_dict["Available"].append(channel.mention)
            elif magewright_role.mention in last_message.content:
                channels_dict["Magewright"].append(channel.mention)
            else:
                channels_dict["In Use"].append(channel.mention)

        original_msg = await dashboard.get_pinned_post(self.bot)
        if original_msg is not None:
            category = dashboard.get_categorychannel(self.bot)
            await original_msg.edit(content='', embed=RpDashboardEmbed(channels_dict, category.name))
        else:
            print(f"Original message not found for msg id [ {dashboard.post_id} ]")

    # --------------------------- #
    # Tasks
    # --------------------------- #

    @tasks.loop(minutes=15.0)
    async def update_rp_dashboards(self):
        print("Starting to update RP channel dashboards")
        start = timer()
        async with self.bot.db.acquire() as conn:
            async for row in conn.execute(get_all_dashboards()):
                dashboard: RpDashboard = RpDashboardSchema().load(row)
                await self.update_dashboard(dashboard)
        end = timer()
        print(f"Channel status dashboards updated in [ {end-start} ]s")
