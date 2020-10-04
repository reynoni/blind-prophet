from discord.ext import commands
from os import listdir, path
import time, logging, os, sys
from datetime import datetime
# from ProphetBot.localsettings import *

dow = datetime.date(datetime.now()).weekday()
logging.basicConfig(level=logging.INFO, filename='log.txt')


class ProphetBot(commands.Bot):
    # Extending/overriding discord.ext.commands.Bot. This should probably be in its own file
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.message.channel.send('Naughty Naughty ' + ctx.message.author.name)
            return


bot = ProphetBot(command_prefix=os.environ['COMMAND_PREFIX'],
                 description='ProphetBot - Created and maintained by Nicoalas#5232 and Alesha#0362',
                 case_insensitive=True)
for filename in listdir('ProphetBot/cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'ProphetBot.cogs.{filename[:-3]}')


@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! Latency is {round(bot.latency * 1000)}ms.')

bot.run(os.environ['bot_token'], bot=True, reconnect=True)
