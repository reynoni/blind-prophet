import asyncio
from discord import ApplicationContext
from discord.ext import commands
from ProphetBot.bot import BpBot


def setup(bot):
    bot.add_cog(listeners(bot))


# TODO: Gotta figure out why this isn't working.
class listeners(commands.Cog):
    bot: BpBot

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        print(f'Cog \'listeners\' loaded')

    @commands.Cog.listener()
    async def on_command_error(self, ctx: ApplicationContext, error) -> None:
        """
        Handle various exceptions and issues

        :param ctx: Context
        :param error: The error that was raised
        """

        # Prevent any commands with local error handling from being handled here
        if hasattr(ctx.command, 'on_error'):
            return

        if isinstance(error, commands.CheckFailure):
            await ctx.respond(f'Do not have required permissions for {ctx.command}')
        else:
            await ctx.respond(f'Something went wrong')
