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


class IncenseView(discord.ui.View):
    def __init__(self, user_id, temple_name):
        super().__init__(timeout=300)
        self.user_id = str(user_id)
        self.temple_name = temple_name
        self.muted = False

    @discord.ui.button(label="🕯️ 領取 3 柱香", style=discord.ButtonStyle.green)
    async def collect(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("這不是你的面板。", ephemeral=True)
            return
        today = datetime.now(timezone(timedelta(hours=8))).date()
        pool = await get_pool()
        async with pool.acquire() as db:
            await db.execute(
                "UPDATE users SET daily_incense=3, last_pray_date=$1 WHERE discord_id=$2",
                today, self.user_id,
            )
        button.disabled = True
        for child in self.children:
            child.disabled = True
        embed = interaction.message.embeds[0]
        embed.description = f"**{self.temple_name}**\n✅ 已領取 3 柱香！使用 `/pray` 膜拜吧。"
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🙏 不持香參拜", style=discord.ButtonStyle.grey)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("這不是你的面板。", ephemeral=True)
            return
        for child in self.children:
            child.disabled = True
        embed = interaction.message.embeds[0]
        embed.description = f"**{self.temple_name}**\n🙏 不持香參拜。隨時可用 `/pray`。"
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="☑️ 今天不再詢問", style=discord.ButtonStyle.blurple, row=1)
    async def mute_today(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("這不是你的面板。", ephemeral=True)
            return
        today = datetime.now(timezone(timedelta(hours=8))).date()
        pool = await get_pool()
        async with pool.acquire() as db:
            await db.execute(
                "UPDATE users SET incense_muted_today=$1 WHERE discord_id=$2",
                today, self.user_id,
            )
        self.muted = True
        button.label = "✅ 已設定今天不再詢問"
        button.disabled = True
        embed = interaction.message.embeds[0]
        embed.description += "\n☑️ 今天不再詢問（已設定）"
        await interaction.response.edit_message(embed=embed, view=self)


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

    @tasks.loop(minutes=1)
    async def price_update_loop(self):
        now = datetime.now(timezone(timedelta(hours=8)))
        current_minutes = now.hour * 60 + now.minute
        do_stocks = current_minutes in (8 * 60, 12 * 60, 16 * 60)
        do_shop = current_minutes % SHOP_PRICE_UPDATE_MINUTES == 0

        if do_stocks or do_shop:
            pool = await get_pool()
            async with pool.acquire() as db:
                if do_stocks:
                    await update_stock_prices(db)
                if do_shop:
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
