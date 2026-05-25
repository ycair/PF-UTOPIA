import asyncio
import sys
import os
import json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import discord
from discord.ext import commands, tasks
from aiohttp import web

from src.config import BOT1_TOKEN, GUILD_ID, STOCK_PRICE_UPDATE_MINUTES, SHOP_PRICE_UPDATE_MINUTES
from src.database import get_pool, init_db, seed_data, update_stock_prices, update_sell_prices
from src.bmc_webhook import create_bmc_app


class UtopiaBot1(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await init_db()
        await seed_data()
        await self.load_extension("src.cogs.registration")
        await self.load_extension("src.cogs.profile")
        await self.load_extension("src.cogs.daily")
        await self.load_extension("src.cogs.inventory")
        await self.load_extension("src.cogs.combat")
        await self.load_extension("src.cogs.faith")
        await self.load_extension("src.cogs.stats_ability")
        await self.load_extension("src.cogs.social")
        await self.load_extension("src.cogs.utility")
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        self.price_update_loop.start()
        self.stamina_regen_loop.start()
        self.travel_check_loop.start()

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.guild is None:
            await message.channel.send(
                "👋 你好！這裡是安逸烏托邦女僕的私訊通道。\n"
                "⚠️ DM 中無法使用任何遊戲指令。\n"
                f"請回到 <#{GUILD_ID}> 伺服器遊玩～"
            )
            return
        await self.process_commands(message)

    @tasks.loop(seconds=15)
    async def travel_check_loop(self):
        TZ_LOOP = timezone(timedelta(hours=8))
        pool = await get_pool()
        async with pool.acquire() as db:
            travelers = await db.fetch(
                "SELECT discord_id FROM users WHERE travel_target IS NOT NULL"
            )
            for t in travelers:
                await self._check_arrival(db, t["discord_id"], TZ_LOOP, 30)

    async def _check_arrival(self, db, user_id, tz, secs_per_dist):
        user = await db.fetchrow(
            "SELECT current_node, travel_target, travel_start FROM users WHERE discord_id=$1",
            user_id,
        )
        if not user or not user["travel_target"] or not user["travel_start"]:
            return
        now = datetime.now(tz)
        start = user["travel_start"]
        if start.tzinfo is None:
            start = start.replace(tzinfo=tz)
        edge = await db.fetchrow(
            "SELECT base_distance FROM map_edges WHERE (from_node=$1 AND to_node=$2) OR (from_node=$2 AND to_node=$1)",
            user["current_node"], user["travel_target"],
        )
        if not edge:
            return
        secs = edge["base_distance"] * secs_per_dist
        if (now - start).total_seconds() >= secs:
            target_id = user["travel_target"]
            await db.execute(
                "UPDATE users SET current_node=travel_target, travel_target=NULL, travel_start=NULL WHERE discord_id=$1",
                user_id,
            )
            target_node = await db.fetchrow(
                "SELECT name, is_safe, node_type FROM map_nodes WHERE id=$1", target_id
            )
            if target_node and target_node["is_safe"] and target_node["node_type"] == "capital":
                await db.execute(
                    "UPDATE users SET current_hp=hp WHERE discord_id=$1", user_id
                )

    @tasks.loop(minutes=STOCK_PRICE_UPDATE_MINUTES)
    async def price_update_loop(self):
        pool = await get_pool()
        async with pool.acquire() as db:
            await update_stock_prices(db)
            await update_sell_prices(db)

    @tasks.loop(minutes=1)
    async def stamina_regen_loop(self):
        pool = await get_pool()
        async with pool.acquire() as db:
            await db.execute(
                "UPDATE users SET stamina=LEAST(stamina+1, max_stamina) WHERE stamina < max_stamina"
            )

    @price_update_loop.before_loop
    async def before_price_update(self):
        await self.wait_until_ready()

    @stamina_regen_loop.before_loop
    async def before_stamina_regen(self):
        await self.wait_until_ready()


async def main():
    bmc_secret = os.getenv("BMC_WEBHOOK_SECRET", "")
    bmc_app = create_bmc_app(bmc_secret)
    bmc_runner = web.AppRunner(bmc_app)
    await bmc_runner.setup()
    bmc_site = web.TCPSite(bmc_runner, "localhost", 8765)
    await bmc_site.start()
    print("💵 Buy Me a Coffee webhook listening on http://localhost:8765/buymecoffee")

    bot = UtopiaBot1()
    await bot.start(BOT1_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
