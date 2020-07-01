from discord.ext import commands
from os import listdir
import time, logging, os, sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
dow = datetime.date(datetime.now()).weekday()
token = ''

bot = commands.Bot(command_prefix='<',description='Test Bot, Not real >.>')

logging.basicConfig(level=logging.INFO, filename='log.txt')
     
@bot.command()
async def load(ctx, ext):
    check = False
    RR = 286360249659817984
    if RR == ctx.author.id:
        check = True
    else:
        await ctx.send("Access Denied.")
    if check == True:
        bot.load_extension(f'cogs.{ext}')
        await ctx.send("Cog Loaded.")
    await ctx.message.delete()
@bot.command()
async def unload(ctx, ext):
    check = False
    RR = 286360249659817984
    if RR == ctx.author.id:
        check = True
    else:
        await ctx.send("Access Denied.")
    if check == True:
        bot.unload_extension(f'cogs.{ext}')
        await ctx.send("Cog Unloaded.")
    await ctx.message.delete()

@bot.command()
async def reload(ctx, ext):
    check = False
    RR = 286360249659817984
    if RR == ctx.author.id:
        check = True
    else:
        await ctx.send("Access Denied.")
    if check == True:
        bot.unload_extension(f'cogs.{ext}')
        bot.load_extension(f'cogs.{ext}')
        await ctx.send("Cogs Reloaded.")
    await ctx.message.delete()

for filename in listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')

@bot.command()
async def list(ctx):
    check = False
    RR = 286360249659817984
    if RR == ctx.author.id:
        check = True
    else:
        await ctx.send("Access Denied.")
    if check == True:
        for filename in listdir('./cogs'):
            if filename.endswith('.py'):
                await ctx.send(f'cogs.{filename[:-3]}')
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


bot.run(token, bot=True,reconnect=True)

