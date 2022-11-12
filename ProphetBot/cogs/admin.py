import asyncio
import datetime
import logging
from discord import SlashCommandGroup, Option, ExtensionAlreadyLoaded, ExtensionNotFound, ExtensionNotLoaded, \
    ApplicationContext
from discord.ext import commands, tasks
from gspread.exceptions import APIError
from os import listdir
from ProphetBot.helpers import is_owner
from ProphetBot.bot import BpBot

log = logging.getLogger(__name__)


 # TODO: Command to modify item
 # TODO: Command to add item
 # TODO: Command to remove item

def setup(bot: commands.Bot):
    bot.add_cog(Admin(bot))


class Admin(commands.Cog):
    bot: BpBot  # Typing annotation for my IDE's sake
    admin_commands = SlashCommandGroup("admin", "Bot administrative commands")

    def __init__(self, bot):
        self.bot = bot
        log.info(f'Cog \'Admin\' loaded')

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(3.0)
        asyncio.ensure_future(self.reload_category_task.start())
        await asyncio.sleep(6.0)
        asyncio.ensure_future(self.reload_item_task.start())

    @admin_commands.command(
        name="load",
        description="Load a cog"
    )
    @commands.check(is_owner)
    async def load_cog(self, ctx: ApplicationContext,
                       cog: Option(str, description="Cog name", required=True)):
        """
        Loads a cog in the bot

        :param ctx: Application context
        :param cog: Cog name to load
        """
        try:
            self.bot.load_extension(f'ProphetBot.cogs.{cog}')
        except ExtensionAlreadyLoaded:
            return await ctx.respond(f'Cog already loaded', ephemeral=True)
        except ExtensionNotFound:
            return await ctx.respond(f'No cog found by the name: {cog}', ephemeral=True)
        except:
            return await ctx.respond(f'Something went wrong', ephemeral=True)
        await ctx.respond(f'Cog Loaded.', ephemeral=True)

    @admin_commands.command(
        name="unload",
        description="Unload a cog"
    )
    @commands.check(is_owner)
    async def unload_cog(self, ctx: ApplicationContext,
                         cog: Option(str, description="Cog name", required=True)):
        """
        Unloads a cog from the bot

        :param ctx: Application context
        :param cog: Cog name to unload
        """
        try:
            self.bot.unload_extension(f'ProphetBot.cogs.{cog}')
        except ExtensionNotLoaded:
            return await ctx.respond(f'Cog was already unloaded', ephemeral=True)
        except ExtensionNotFound:
            return await ctx.respond(f'No cog found by the name: {cog}', ephemeral=True)
        except:
            return await ctx.respond(f'Something went wrong', ephemeral=True)
        await ctx.respond(f'Cog unloaded', ephemeral=True)

    # TODO: Once compendium is up and running reload that too in place of sheets
    @admin_commands.command(
        name="reload",
        description="Reloads either a specific cog, refresh DB information, or reload everything"
    )
    @commands.check(is_owner)
    async def reload_cog(self, ctx: ApplicationContext,
                         cog: Option(str, description="Cog name, ALL, or SHEET", required=True)):
        """
        Used to reload a cog, refresh DB information, or reload all cogs and DB information

        :param ctx: Context
        :param cog: cog to reload, SHEET to reload sheets, ALL to reload all
        """
        await ctx.defer()

        if str(cog).upper() == 'ALL':
            for file_name in listdir('./ProphetBot/cogs'):
                if file_name.endswith('.py'):
                    ext = file_name.replace('.py', '')
                    self.bot.unload_extension(f'ProphetBot.cogs.{ext}')
                    self.bot.load_extension(f'ProphetBot.cogs.{ext}')
            await ctx.respond("All cogs reloaded")
            await self._reload_sheets(ctx)
        elif str(cog).upper() in ['SHEETS', 'SHEET']:  # TODO: Remove this once we get rid of GSheets
            await self._reload_sheets(ctx)
            await ctx.respond(f'Done')
        elif str(cog).upper() in ['DB', 'COMPENDIUM']:
            await self._reload_DB(ctx)
            await ctx.respond(f'Done')
        elif str(cog).upper() in ['INVENTORY']:
            await self._reload_items(ctx)
            await ctx.respond(f'Done')
        else:
            try:
                self.bot.unload_extension(f'ProphetBot.cogs.{cog}')
            except ExtensionNotLoaded:
                return await ctx.respond(f'Cog was already unloaded', ephemeral=True)
            except ExtensionNotFound:
                return await ctx.respond(f'No cog found by the name: {cog}', ephemeral=True)
            except:
                return await ctx.respond(f'Something went wrong', ephemeral=True)

            self.bot.load_extension(f'ProphetBot.cogs.{cog}')
            await ctx.respond(f'Cog {cog} reloaded')

    @admin_commands.command(
        name="list",
        description="List out all cogs"
    )
    @commands.check(is_owner)
    async def list(self, ctx: ApplicationContext):
        """
        List all cogs

        :param ctx: Context
        """

        files = []
        for file_name in listdir('./ProphetBot/cogs'):
            if file_name.endswith('.py'):
                files.append(file_name[:-3])
        await ctx.respond("\n".join(files))

    @admin_commands.command(
        name="test"
    )
    async def test(self, ctx: ApplicationContext):
        dt = datetime.datetime.utcnow()
        day = dt.weekday()
        await ctx.respond(f"dt: {dt} and day {day}")

    # --------------------------- #
    # Private Methods
    # --------------------------- #

    async def _reload_sheets(self, ctx):
        await ctx.trigger_typing()
        try:
            self.bot.sheets.reload()
        except APIError as e:
            await ctx.send(f"Error opening BPdia sheet(s)\n\n"
                           f"**Details:**\n"
                           f"{e}")
            return
        await ctx.send("Connection to BPdia reloaded")

    async def _reload_DB(self, ctx):
        await self.bot.compendium.reload_categories(self.bot)
        await ctx.send("Compendium reloaded")

    async def _reload_items(self, ctx):
        await self.bot.compendium.load_items(self.bot)
        await ctx.send("Items reloading")

    # --------------------------- #
    # Tasks
    # --------------------------- #
    @tasks.loop(minutes=30)
    async def reload_category_task(self):
        await self.bot.compendium.reload_categories(self.bot)

    @tasks.loop(hours=24)
    async def reload_item_task(self):
        await self.bot.compendium.load_items(self.bot)
