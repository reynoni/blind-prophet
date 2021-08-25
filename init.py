import logging
import os
from datetime import datetime
from os import listdir

import discord
from discord import Intents
from discord.ext import commands

from ProphetBot.bot import BP_Bot

dow = datetime.date(datetime.now()).weekday()
logging.basicConfig(level=logging.INFO, filename='log.txt')
intents = Intents.default()
intents.members = True


class MyHelpCommand(commands.MinimalHelpCommand):
    async def send_pages(self):
        destination = self.get_destination()
        e = discord.Embed(color=discord.Color.blurple(), description='')
        for page in self.paginator.pages:
            e.description += page
        await destination.send(embed=e)


bot = BP_Bot(command_prefix=os.environ['COMMAND_PREFIX'],
             description='ProphetBot - Created and maintained by Nicoalas#5232 and Alesha#0362',
             case_insensitive=True,
             help_command=MyHelpCommand(),
             intents=intents)

for filename in listdir('ProphetBot/cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'ProphetBot.cogs.{filename[:-3]}')


@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! Latency is {round(bot.latency * 1000)}ms.')


bot.run(os.environ['bot_token'], bot=True, reconnect=True)
