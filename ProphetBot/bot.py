import os

import aiopg.sa
from aiopg.sa import create_engine
from discord.ext import commands
from timeit import default_timer as timer

from sqlalchemy.schema import CreateTable

from ProphetBot.sheets_client import GsheetsClient
from ProphetBot.models.db import arenas_table, category_dashboards_table, global_staging_table, global_players_table


async def create_tables(conn: aiopg.sa.SAConnection):
    await conn.execute(CreateTable(arenas_table, if_not_exists=True))
    await conn.execute(CreateTable(category_dashboards_table, if_not_exists=True))
    await conn.execute(CreateTable(global_staging_table, if_not_exists=True))
    await conn.execute(CreateTable(global_players_table, if_not_exists=True))


class BpBot(commands.Bot):
    sheets: GsheetsClient
    db: aiopg.sa.Engine

    # Extending/overriding discord.ext.commands.Bot
    def __init__(self, **options):
        super(BpBot, self).__init__(**options)
        self.sheets = GsheetsClient()

    async def on_ready(self):
        start = timer()
        self.db = await create_engine(os.environ["DATABASE_URL"])
        end = timer()

        print(f"Time to create db engine: {end - start}")
        async with self.db.acquire() as conn:
            await create_tables(conn)

        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")
