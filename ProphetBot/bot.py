from discord.ext import commands
from ProphetBot.sheets_client import gsheetsClient


class BP_Bot(commands.Bot):
    # Extending/overriding discord.ext.commands.Bot. This should probably be in its own file
    def __init__(self, **options):
        super(BP_Bot, self).__init__(**options)
        self.sheets = gsheetsClient()

    # async def on_command_error(self, ctx: commands.context.Context, error):
