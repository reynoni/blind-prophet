from discord.ext import commands
from ProphetBot.sheets_client import GsheetsClient


class BpBot(commands.Bot):
    sheets: GsheetsClient

    # Extending/overriding discord.ext.commands.Bot
    def __init__(self, **options):
        super(BpBot, self).__init__(**options)
        self.sheets = GsheetsClient()
