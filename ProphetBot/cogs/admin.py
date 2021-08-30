from discord.ext import commands
from gspread.exceptions import APIError
from os import listdir
from ProphetBot.helpers import *
from ProphetBot.bot import BP_Bot


def setup(bot):
    bot.add_cog(Admin(bot))


class Admin(commands.Cog):
    bot: BP_Bot  # Typing annotation for my IDE's sake

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
    @commands.has_role('Council')
    async def reload(self, ctx, ext):
        if str(ext).upper() == 'ALL':
            for file_name in listdir('./ProphetBot/cogs'):
                if file_name.endswith('.py'):
                    ext = file_name.replace('.py', '')
                    self.bot.unload_extension(f'ProphetBot.cogs.{ext}')
                    self.bot.load_extension(f'ProphetBot.cogs.{ext}')
            await ctx.send("All cogs reloaded")
            await self._reload_sheets(ctx)
        elif str(ext).upper() in ['SHEETS', 'BPDIA']:
            await self._reload_sheets(ctx)
        else:
            self.bot.unload_extension(f'ProphetBot.cogs.{ext}')
            self.bot.load_extension(f'ProphetBot.cogs.{ext}')
            await ctx.send(f"Cog '{ext}' reloaded")
        await ctx.message.delete()

    @commands.command()
    @commands.check(is_admin)
    async def list(self, ctx):
        for file_name in listdir('./ProphetBot/cogs'):
            if file_name.endswith('.py'):
                await ctx.send(f'`ProphetBot.cogs.{file_name[:-3]}`')
        await ctx.message.delete()

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
