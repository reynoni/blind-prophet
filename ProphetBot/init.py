from discord.ext import commands
from os import listdir
import time, logging, os, sys
from datetime import datetime
from ProphetBot.localsettings import *

dow = datetime.date(datetime.now()).weekday()
logging.basicConfig(level=logging.INFO, filename='log.txt')


class ProphetBot(commands.Bot):
    # Extending/overriding discord.ext.commands.Bot. This should probably be in its own file
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.message.channel.send('Naughty Naughty ' + ctx.message.author.name)
            return


bot = ProphetBot(command_prefix=COMMAND_PREFIX, description=BOT_DESCRIPTION)
for filename in listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')


@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! Latency is {round(bot.latency * 1000)}ms.')

bot.run(token, bot=True, reconnect=True)
