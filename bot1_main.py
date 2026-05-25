import asyncio
import sys
import os

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
