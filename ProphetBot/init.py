from discord.ext import commands
from os import listdir
import time, logging, os, sys
from datetime import datetime
from ProphetBot.localsettings import token
# from ProphetBot.constants import *
from ProphetBot.helpers import *
dow = datetime.date(datetime.now()).weekday()

bot = commands.Bot(command_prefix='<', description='Test Bot, Not real >.>')

logging.basicConfig(level=logging.INFO, filename='log.txt')


@bot.command()
@commands.check(is_admin)
async def load(ctx, ext):
    bot.load_extension(f'cogs.{ext}')
    await ctx.send("Cog Loaded.")
    await ctx.message.delete()


@bot.command()
@commands.check(is_admin)
async def unload(ctx, ext):
    bot.unload_extension(f'cogs.{ext}')
    await ctx.send("Cog Unloaded.")
    await ctx.message.delete()


@bot.command()
@commands.check(is_admin)
async def reload(ctx, ext):
    bot.unload_extension(f'cogs.{ext}')
    bot.load_extension(f'cogs.{ext}')
    await ctx.send("Cogs Reloaded.")
    await ctx.message.delete()


@bot.command()
@commands.check(is_admin)
async def list(ctx):
    for file_name in listdir('./cogs'):
        if file_name.endswith('.py'):
            await ctx.send(f'cogs.{file_name[:-3]}')
    await ctx.message.delete()


@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! Latency is {round(bot.latency * 1000)}ms.')


@load.error
@unload.error
@reload.error
@list.error
async def error_handler(self, ctx, error):  # TODO: Move this check to a universal on_command_error() override
    if isinstance(error, commands.CheckFailure):
        await ctx.message.channel.send('Naughty Naughty ' + ctx.message.author.name)
        return

bot.run(token, bot=True, reconnect=True)

