import asyncio
import logging
import sys
import traceback
from os import listdir
import discord
from discord import Intents, ApplicationContext
from discord.ext import commands
from ProphetBot.bot import BpBot
from ProphetBot.constants import BOT_TOKEN, DEFAULT_PREFIX, DEBUG_GUILDS

intents = Intents.default()
intents.members = True
intents.message_content = True

# TODO: Error embeds instead of straight ctx.responds for consistency


class MyHelpCommand(commands.MinimalHelpCommand):
    async def send_pages(self):
        destination = self.get_destination()
        e = discord.Embed(color=discord.Color.blurple(), description='')
        for page in self.paginator.pages:
            e.description += page
        await destination.send(embed=e)


log_formatter = logging.Formatter("%(asctime)s %(name)s: %(message)s")
handler = logging.StreamHandler(sys.stdout)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)
log = logging.getLogger("bot")

# Because Windows is terrible
if sys.version_info >= (3, 8) and sys.platform.lower().startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

bot = BpBot(command_prefix=DEFAULT_PREFIX,
            description='ProphetBot - Created and maintained by Nick!#8675 and Alesha#0362',
            case_insensitive=True,
            help_command=MyHelpCommand(),
            intents=intents,
            debug_guilds=DEBUG_GUILDS
            )

for filename in listdir('ProphetBot/cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'ProphetBot.cogs.{filename[:-3]}')


@bot.command()
async def ping(ctx):
    print("Pong")
    await ctx.send(f'Pong! Latency is {round(bot.latency * 1000)}ms.')


@bot.event
async def on_application_command_error(ctx: ApplicationContext, error):
    """
    Handle various exceptions and issues

    :param ctx: Context
    :param error: The error that was raised
    """

    # Prevent any commands with local error handling from being handled here
    if hasattr(ctx.command, 'on_error'):
        return

    if isinstance(error, discord.errors.CheckFailure):
        return await ctx.respond(f'You do not have required permissions for `{ctx.command}`')
    else:
        log.warning("Error in command: '{}'".format(ctx.command))
        for line in traceback.format_exception(type(error), error, error.__traceback__):
            log.warning(line)
        return await ctx.respond(f'Something went wrong. Let us know if it keeps up!')


@bot.event
async def on_application_command(ctx):
    try:
        params = "".join([f" [{p['name']}: {p['value']}]" for p in ctx.selected_options])
        log.info(
            "cmd: chan {0.channel} [{0.channel.id}], serv: {0.guild} [{0.guild.id}],"
            "auth: {0.user} [{0.user.id}]: {0.command} ".format(ctx) + params
        )
    except AttributeError:
        log.info("Command in PM with {0.message.author} ({0.message.author.id}): {0.message.content}.".format(ctx))


bot.run(BOT_TOKEN)
