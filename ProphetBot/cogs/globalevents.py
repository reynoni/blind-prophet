from discord import *
from discord.ext import commands
from ProphetBot.bot import BpBot
from ProphetBot.helpers import calc_amt, confirm
from ProphetBot.models.db_objects import gEvent, gPlayer
from ProphetBot.models.embeds import GlobalEmbed
from discord.commands import SlashCommandGroup

from ProphetBot.models.schemas import gEventSchema, gPlayerSchema
from ProphetBot.models.sheets_objects import GlobalHost, GlobalModifier, GlobalEntry
from ProphetBot.queries import get_active_global, insert_new_global_event, update_global_event, close_global_event, \
    add_global_player, update_global_channels, get_all_global_players, update_global_player


def setup(bot):
    bot.add_cog(GlobalEvent(bot))


async def get_all_players(self, event_id: int) -> []:
    players = []

    async with self.bot.db.acquire() as conn:
        async for row in conn.execute(get_all_global_players(event_id)):
            player: gPlayer = gPlayerSchema().load(row)
            players.append(player)
    return players


class GlobalEvent(commands.Cog):
    bot: BpBot  # Typing annotation for my IDE's sake
    global_event_commands = SlashCommandGroup("global_event", "Commands related to global event management.")

    def __init__(self, bot):
        self.bot = bot

        print(f'Cog \'Global\' loaded')

    @global_event_commands.command(
        name="new_event",
        description="Create a new global event",
    )
    async def gb_new(self, ctx: ApplicationContext,
                     gname: Option(str, description="Global event name", required=True),
                     gold: Option(int, description="Base gold for the event", required=True),
                     exp: Option(int, description="Base experience for the event", required=True),
                     combat: Option(bool, description="Indicated if this is a global event or not. If true then "
                                                      "ignores mod", required=False, default=False),
                     mod: Option(str, description="Base modifier for the event",
                                 choices=GlobalModifier.optionchoice_list(), required=False)):
        await ctx.defer()

        async with self.bot.db.acquire() as conn:
            results = await conn.execute(get_active_global(ctx.guild_id))
            gRow = await results.first()

        if gRow is not None:
            await ctx.respond(f'Error: Already an active global event', ephemeral=True)
            return

        if mod is None:
            mod = "Medium"

        globEvent = gEvent(name=gname, base_gold=gold, base_exp=exp, base_mod=mod, combat=combat, channels=[],
                           guild_id=ctx.guild_id,
                           active=True)

        async with self.bot.db.acquire() as conn:
            await conn.execute(insert_new_global_event(globEvent.guild_id, globEvent.name, globEvent.base_gold,
                                                       globEvent.base_exp, globEvent.base_mod, globEvent.combat))

        await ctx.respond(embed=GlobalEmbed(ctx=ctx, globEvent=globEvent))

    @global_event_commands.command(
        name="update_event",
        description="Change global event defaults"
    )
    async def gb_update(self, ctx: ApplicationContext,
                        gname: Option(str, description="Global event name", required=False),
                        gold: Option(int, description="Base gold for the event", required=False),
                        exp: Option(int, description="Base experience for the event", required=False),
                        mod: Option(str, description="Base modifier for the event",
                                    choices=GlobalModifier.optionchoice_list(), required=False),
                        combat: Option(bool, description="Indicated if this is a global event or not. If true then "
                                                         "ignores mod", required=False, default=False)):
        await ctx.defer()

        async with self.bot.db.acquire() as conn:
            results = await conn.execute(get_active_global(ctx.guild_id))
            gRow = await results.first()

        if gRow is None:
            await ctx.respond(f'Error: No active global event on this server', ephemeral=True)
            return
        elif gname is None and gold is None and exp is None and mod is None and combat is None:
            await ctx.respond(f'Error: Nothing given to update', ephemeral=True)
            return

        globEvent: gEvent = gEventSchema().load(gRow)
        oldMod = globEvent.base_mod

        if gname is not None:
            globEvent.name = gname

        if gold is not None:
            globEvent.base_gold = gold

        if exp is not None:
            globEvent.base_exp = exp

        if mod is not None:
            globEvent.base_mod = mod

        if combat is not None:
            globEvent.combat = combat

        async with self.bot.db.acquire() as conn:
            await conn.execute(
                update_global_event(globEvent.event_id, globEvent.name, globEvent.base_gold, globEvent.base_exp,
                                    globEvent.base_mod, globEvent.combat))

        if gold or exp or mod or combat is not None:
            players = await get_all_players(self=self, event_id=globEvent.event_id)
            for p in players:
                if p.active and p.update:
                    bGold = globEvent.base_gold if gold is None else gold
                    bExp = globEvent.base_exp if exp is None else exp

                    if p.modifier == oldMod:
                        bMod = globEvent.base_mod if mod is None else mod
                    else:
                        bMod = p.modifier

                    p.gold = bGold if globEvent.combat else calc_amt(bGold, bMod, p.host)
                    p.exp = bExp if globEvent.combat else calc_amt(bExp, bMod, p.host)

                    async with self.bot.db.acquire() as conn:
                        await conn.execute(
                            update_global_player(id=p.id, modifier=p.modifier, host=p.host, gold=p.gold, exp=p.exp,
                                                 update=p.update, active=p.active))

        await ctx.respond(embed=GlobalEmbed(ctx, globEvent, players))

    #
    @global_event_commands.command(
        name="purge_event",
        description="Purge all global event currently staged"
    )
    async def gb_purge(self, ctx: ApplicationContext):
        await ctx.defer()

        async with self.bot.db.acquire() as conn:
            results = await conn.execute(get_active_global(ctx.guild_id))
            gRow = await results.first()

        if gRow is None:
            await ctx.respond(f'Error: No active global event on this server', ephemeral=True)
            return

        globEvent: gEvent = gEventSchema().load(gRow)

        async with self.bot.db.acquire() as conn:
            await conn.execute(close_global_event(globEvent.event_id))

        embed = Embed(title="Global purge")
        embed.set_footer(text="Sickness must be purged!")
        embed.set_image(url="https://cdn.discordapp.com/attachments/987038574245474304/1022686290908561408/unknown.png")

        await ctx.respond(embed=embed)

    @global_event_commands.command(
        name="scrape",
        description="Scrapes a channel and adds the non-bot users to the global event"
    )
    async def gb_scrape(self, ctx: ApplicationContext,
                        channel: Option(TextChannel, description="Channel to pull players from", required=True)):
        await ctx.defer()

        async with self.bot.db.acquire() as conn:
            results = await conn.execute(get_active_global(ctx.guild_id))
            gRow = await results.first()

        if gRow is None:
            await ctx.respond(f'Error: No active global event on this server', ephemeral=True)
            return

        globEvent: gEvent = gEventSchema().load(gRow)

        players = await get_all_players(self=self, event_id=globEvent.event_id)
        messages = await channel.history(oldest_first=True).flatten()

        for msg in messages:
            if msg.author.bot == False and msg.author.id not in [p.player_id for p in players]:
                player = gPlayer(player_id=msg.author.id, global_id=globEvent.event_id, modifier=globEvent.base_mod,
                                 host=None,
                                 gold=globEvent.base_gold if not globEvent.combat else calc_amt(globEvent.base_gold,
                                                                                                globEvent.base_mod),
                                 exp=globEvent.base_exp if not globEvent.combat else calc_amt(globEvent.base_exp,
                                                                                              globEvent.base_mod),
                                 update=True, active=True
                                 )
                players.append(player)
                async with self.bot.db.acquire() as conn:
                    await conn.execute(
                        add_global_player(event_id=player.global_id, player_id=player.player_id,
                                          modifier=player.modifier, host=player.host, gold=player.gold,
                                          exp=player.exp, update=player.update, active=player.active))

        if channel.id not in globEvent.channels:
            globEvent.channels.append(channel.id)
            async with self.bot.db.acquire() as conn:
                await conn.execute(update_global_channels(globEvent.event_id, globEvent.channels))

        await ctx.respond(embed=GlobalEmbed(ctx, globEvent, players))

    @global_event_commands.command(
        name="player_update",
        description="Fine tune a player, or add a player. Will re-activate a player if previously inactive"
    )
    async def gb_user_update(self, ctx: ApplicationContext,
                             pid: Option(Member, description="Player to add/modify", required=True),
                             mod: Option(str, description="Players effort modifier",
                                         choices=GlobalModifier.optionchoice_list(), required=False),
                             host: Option(str, description="Players host status",
                                          choices=GlobalHost.optionchoice_list(), required=False),
                             gold: Option(int,
                                          description="Players gold reward. NOTE: This will disable auto-calculation "
                                                      "for a user",
                                          required=False),
                             exp: Option(int,
                                         description="Players exp reward. NOTE: This will disable auto-calculation "
                                                     "for a user",
                                         required=False)):
        await ctx.defer()

        async with self.bot.db.acquire() as conn:
            results = await conn.execute(get_active_global(ctx.guild_id))
            gRow = await results.first()

        if gRow is None:
            await ctx.respond(f'Error: No active global event on this server', ephemeral=True)
            return

        globEvent: gEvent = gEventSchema().load(gRow)

        players = await get_all_players(self=self, event_id=globEvent.event_id)

        if gold or exp is not None:
            update = False
        else:
            update = True

        if pid.id not in [p.player_id for p in players]:
            bGold = globEvent.base_gold if gold is None else gold
            bExp = globEvent.base_exp if exp is None else exp
            bMod = globEvent.base_mod if mod is None else mod
            bHost = None if host is None else host

            player = gPlayer(player_id=pid.id, global_id=globEvent.event_id, modifier=bMod, host=bHost,
                             gold=calc_amt(bGold, bMod, bHost) if update else bGold,
                             exp=calc_amt(bExp, bMod, bHost) if update else bGold,
                             update=update, active=True)
            players.append(player)
            async with self.bot.db.acquire() as conn:
                await conn.execute(
                    add_global_player(event_id=player.global_id, player_id=player.player_id,
                                      modifier=player.modifier, host=player.host, gold=player.gold,
                                      exp=player.exp, update=player.update, active=player.active))
        else:
            player = next((p for p in players if p.player_id == pid.id), None)
            bGold = globEvent.base_gold if gold is None else gold
            bExp = globEvent.base_exp if exp is None else exp
            bMod = globEvent.base_mod if mod is None else mod
            bHost = None if host is None else host

            player.gold = calc_amt(bGold, bMod, bHost) if update and not globEvent.combat else bGold
            player.exp = calc_amt(bExp, bMod, bHost) if update and not globEvent.combat else bExp
            player.modifier = bMod
            player.host = bHost
            player.update = update
            player.active = True

            async with self.bot.db.acquire() as conn:
                await conn.execute(
                    update_global_player(id=player.id, modifier=player.modifier, host=player.host, gold=player.gold,
                                         exp=player.exp, update=player.update, active=player.active)
                )

        await ctx.respond(embed=GlobalEmbed(ctx, globEvent, players))

    @global_event_commands.command(
        name="remove",
        description="Remove a player from the global event"
    )
    async def gb_remove(self, ctx: ApplicationContext,
                        pid: Option(Member, description="Player to remove from the Global Event", required=True)):
        await ctx.defer()

        async with self.bot.db.acquire() as conn:
            results = await conn.execute(get_active_global(ctx.guild_id))
            gRow = await results.first()

        if gRow is None:
            await ctx.respond(f'Error: No active global event on this server', ephemeral=True)
            return

        globEvent: gEvent = gEventSchema().load(gRow)

        players = await get_all_players(self=self, event_id=globEvent.event_id)

        if pid.id not in [p.player_id for p in players]:
            await ctx.respond(f'Player is not in the current global event', ephemeral=True)

        player = next((p for p in players if p.player_id == pid.id), None)

        if not player.active:
            await ctx.respond(f'Player is already inactive for the global', ephemeral=True)
        else:
            async with self.bot.db.acquire() as conn:
                await conn.execute(
                    update_global_player(player.id, player.modifier, player.host, player.gold, player.exp,
                                         player.update, False)
                )

        await ctx.respond(embed=GlobalEmbed(ctx, globEvent, players))

    @global_event_commands.command(
        name="review",
        description="Review the currently staged global event information"
    )
    async def gb_review(self, ctx: ApplicationContext,
                        gblist: Option(bool, description="Whether to list out all players in the global", required=True,
                                       default=False)):
        await ctx.defer()

        async with self.bot.db.acquire() as conn:
            results = await conn.execute(get_active_global(ctx.guild_id))
            gRow = await results.first()

        if gRow is None:
            await ctx.respond(f'Error: No active global event on this server', ephemeral=True)
            return
        else:
            globEvent: gEvent = gEventSchema().load(gRow)
            players = await get_all_players(self=self, event_id=globEvent.event_id)
            await ctx.respond(embed=GlobalEmbed(ctx, globEvent, players, gblist))

    @global_event_commands.command(
        name="commit",
        description="Commits the global rewards"
    )
    async def gb_commit(self, ctx: ApplicationContext):
        await ctx.defer()

        async with self.bot.db.acquire() as conn:
            results = await conn.execute(get_active_global(ctx.guild_id))
            gRow = await results.first()

        if gRow is None:
            await ctx.respond(f'Error: No active global event on this server', ephemeral=True)
            return

        to_end = await confirm(ctx, "Are you sure you want to log this global? (Reply with yes/no)", True)

        if to_end is None:
            await ctx.respond(f'Timed out waiting for a response or invalid response.', delete_after=10)
            return
        elif not to_end:
            await ctx.respond(f'Ok, cancelling.', delete_after=10)
            return

        globEvent: gEvent = gEventSchema().load(gRow)
        players = await get_all_players(self=self, event_id=globEvent.event_id)
        characters = self.bot.sheets.get_all_characters()
        fail_players = []
        log_list = []

        for p in players:
            character = next((c for c in characters if c.player_id == p.player_id), None)
            if p.active:
                if not character:
                    fail_players.append(p)
                else:
                    log_entry = GlobalEntry(f"{ctx.author.name}#{ctx.author.discriminator}", character, globEvent.name,
                                            p.gold, p.exp)
                    log_list.append(log_entry)

        self.bot.sheets.log_activities(log_list)

        async with self.bot.db.acquire() as conn:
            await conn.execute(close_global_event(globEvent.event_id))

        embed = Embed(title=f"Global: {globEvent.name} - has been logged")
        embed.add_field(name="**# of Entries**",
                        value=f"{len(log_list)}",
                        inline=False)

        if fail_players:
            embed.add_field(name="**Failed entries due to player not having an active character**",
                            value="\n".join([f"\u200b {p.get_name(ctx)}" for p in fail_players]))

        await ctx.respond(embed=embed)

    @global_event_commands.command(
        name="help",
        description="Summary of the global event command group"
    )
    async def gb_help(self, ctx: ApplicationContext):
        embed = Embed(title=f"**Global Events Command Group Overview**")
        embed.add_field(name="**Overview of the group**",
                        value=f"This group is used to help manage and stage a global event. This will allow for the "
                              f"creation, administration, and changes to an event without actually committing. "
                              f"The primary intent is to be able to log event rewards for multiple players without "
                              f"having to do individual commands for each player\n\n"
                              f"**Only one (1) global event can be running at a time**",
                        inline=False)

        embed.add_field(name=f"**How Rewards are calculated**",
                        value=f"*Combat global* - All players and hosts receive the base gold/exp unless otherwise "
                              f"modified\n\n"
                              f"*Non-combat global* - Players will receive base gold/exp * effort modifier capped at"
                              f"a defined maximum per modifier\n"
                              f"__Modifier multipliers:__ High (1.25), Medium (1.00), Low (0.75)\n"
                              f"__Defined maximum:__ High (250), Medium (200), Low (150)\n\n"
                              f"*Hosts* - Players flagged as hosts will have different rewards\n"
                              f"__Participating__ - Player will get their participation rewards from above + 100\n"
                              f"__Hosting Only__ - Player will not participation rewards, rather the equivalent of 100 "
                              f"+ a Low effort modified reward",
                        inline=False)

        embed.add_field(name=f"Commands",
                        value=f"**new_event** - Creates a new global event\n"
                              f"**update_event** - Updates information for an event\n"
                              f"**purge_event** - Clears out the currently staged event. "
                              f"Used if there are a bunch of mistakes\n"
                              f"**scrape** - Scrapes a given channel, and adds all the non-bot users to the event"
                              f"with the default settings\n"
                              f"**player_update** - Updates a given players details, or manually add a player "
                              f"to the event\n"
                              f"**remove** - Manually removes a player from the global event\n"
                              f"**review** - Shows the standard global embed with the option to list all the "
                              f"active players\n"
                              f"**commit** - Will log the event and clear it out (no need to purge after this\n"
                              f"**help** - Bruh.....",
                        inline=False)

        await ctx.respond(embed=embed)
