from discord.ext import commands
from os import listdir
import time, logging, os, sys
from datetime import datetime
from ProphetBot.localsettings import token
from ProphetBot.constants import *
# from ProphetBot.cogs.helpers import *
dow = datetime.date(datetime.now()).weekday()
# token = ''  # NEVER COMMIT THIS

bot = commands.Bot(command_prefix='<', description='Test Bot, Not real >.>')

logging.basicConfig(level=logging.INFO, filename='log.txt')


@bot.command()
async def load(ctx, ext):
    if ctx.author.id in ADMIN_USERS:
        bot.load_extension(f'cogs.{ext}')
        await ctx.send("Cog Loaded.")
    else:
        await ctx.send("Access Denied.")
    await ctx.message.delete()


@bot.command()
async def unload(ctx, ext):
    if ctx.author.id in ADMIN_USERS:
        bot.unload_extension(f'cogs.{ext}')
        await ctx.send("Cog Unloaded.")
    else:
        await ctx.send("Access Denied.")
    await ctx.message.delete()


@bot.command()
async def reload(ctx, ext):
    if ctx.author.id in ADMIN_USERS:
        bot.unload_extension(f'cogs.{ext}')
        bot.load_extension(f'cogs.{ext}')
        await ctx.send("Cogs Reloaded.")
    else:
        await ctx.send("Access Denied.")
    await ctx.message.delete()

for filename in listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')


@bot.command()
async def list(ctx):
    if ctx.author.id in ADMIN_USERS:
        for filename in listdir('./cogs'):
            if filename.endswith('.py'):
                await ctx.send(f'cogs.{filename[:-3]}')
    else:
        await ctx.send("Access Denied.")
    await ctx.message.delete()


@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! Latency is {round(bot.latency * 1000)}ms.')

##print(f'{dow}')  
##if dow == 6:
##    run = True
##else:
##    run = False
##    
##while True:
##    if (dow == 1) & (run == False):
##        weekly()
##        run = True
##    else:
##        time.sleep(60)
##        print("slept")


bot.run(token, bot=True, reconnect=True)

