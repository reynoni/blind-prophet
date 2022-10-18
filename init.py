import asyncio
import os
import sys
from os import listdir
import discord
from discord import Intents
from discord.ext import commands
from ProphetBot.bot import BpBot

intents = Intents.default()
intents.members = True
intents.message_content = True


class MyHelpCommand(commands.MinimalHelpCommand):
    async def send_pages(self):
        destination = self.get_destination()
        e = discord.Embed(color=discord.Color.blurple(), description='')
        for page in self.paginator.pages:
            e.description += page
        await destination.send(embed=e)


# Because Windows is terrible
if sys.version_info >= (3, 8) and sys.platform.lower().startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

bot = BpBot(command_prefix=os.environ['COMMAND_PREFIX'],
            description='ProphetBot - Created and maintained by Nick!#8675 and Alesha#0362',
            case_insensitive=True,
            help_command=MyHelpCommand(),
            intents=intents,
            debug_guilds=[os.environ.get("GUILD", [])])

for filename in listdir('ProphetBot/cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'ProphetBot.cogs.{filename[:-3]}')

@bot.command()
async def ping(ctx):
    print("Pong")
    await ctx.send(f'Pong! Latency is {round(bot.latency * 1000)}ms.')




bot.run(os.environ['BOT_TOKEN'])
