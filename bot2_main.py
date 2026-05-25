import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import discord
from discord.ext import commands

from src.config import BOT2_TOKEN, GUILD_ID, STOCK_PRICE_UPDATE_MINUTES
from src.database import get_pool, init_db, update_stock_prices, update_sell_prices


class UtopiaBot2(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.load_extension("src.cogs.shop")
        await self.load_extension("src.cogs.lottery")
        await self.load_extension("src.cogs.investment")
        await self.load_extension("src.cogs.pet")
        await self.load_extension("src.cogs.achievements")
        await self.load_extension("src.cogs.ranking")
        await self.load_extension("src.cogs.events")
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def on_ready(self):
        print(f"Bot ② logged in as {self.user}")


async def main():
    await init_db()
    bot = UtopiaBot2()
    await bot.start(BOT2_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
