from discord.ext import commands
from os import listdir
from ProphetBot.helpers import *


def setup(bot):
    bot.add_cog(Admin(bot))


class Admin(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        print(f'Cog \'Admin\' loaded')

    @commands.command()
    @commands.check(is_admin)
    async def load(self, ctx, ext):
        self.bot.load_extension(f'ProphetBot.cogs.{ext}')
        await ctx.send("Cog Loaded.")
        await ctx.message.delete()

    @commands.command()
    @commands.check(is_admin)
    async def unload(self, ctx, ext):
        self.bot.unload_extension(f'ProphetBot.cogs.{ext}')
        await ctx.send("Cog Unloaded.")
        await ctx.message.delete()

    @commands.command()
    @commands.check(is_admin)
    async def reload(self, ctx, ext):
        if str(ext).upper() == 'ALL':
            for file_name in listdir('./ProphetBot/cogs'):
                if file_name.endswith('.py'):
                    ext = file_name.replace('.py', '')
                    self.bot.unload_extension(f'ProphetBot.cogs.{ext}')
                    self.bot.load_extension(f'ProphetBot.cogs.{ext}')
        else:
            self.bot.unload_extension(f'ProphetBot.cogs.{ext}')
            self.bot.load_extension(f'ProphetBot.cogs.{ext}')
        await ctx.send("Cogs Reloaded.")
        await ctx.message.delete()

    @commands.command()
    @commands.check(is_admin)
    async def list(self, ctx):
        for file_name in listdir('./ProphetBot/cogs'):
            if file_name.endswith('.py'):
                await ctx.send(f'`ProphetBot.cogs.{file_name[:-3]}`')
        await ctx.message.delete()
