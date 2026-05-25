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
    def __init__(self, user_id, temple_name, timeout=120):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.temple_name = temple_name

    @discord.ui.button(label="🕯️ 領取 3 柱香", style=discord.ButtonStyle.green)
    async def collect(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != str(self.user_id):
            await interaction.response.send_message("這不是你的面板。", ephemeral=True)
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            today = datetime.now(timezone(timedelta(hours=8))).date()
            await db.execute(
                "UPDATE users SET daily_incense=3, last_pray_date=$1 WHERE discord_id=$2",
                today, str(self.user_id),
            )
        button.disabled = True
        button.label = "✅ 已領取"
        embed = interaction.message.embeds[0]
        embed.description = f"**{self.temple_name}**\n✅ 已領取 3 柱香！使用 `/pray` 膜拜吧。"
        embed.set_footer(text="🛡️ 鬼王庇佑")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="❌ 不需要", style=discord.ButtonStyle.grey)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != str(self.user_id):
            await interaction.response.send_message("這不是你的面板。", ephemeral=True)
            return
        embed = interaction.message.embeds[0]
        embed.description = f"**{self.temple_name}**"
        embed.set_footer(text="🛡️ 鬼王庇佑")
        await interaction.response.edit_message(embed=embed, view=None)


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
            "SELECT current_node, travel_target, travel_start, travel_path, "
            "travel_message_id, travel_channel_id, sprint_until FROM users WHERE discord_id=$1",
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

        sprint_until = user.get("sprint_until")
        speed_mult = 0.0
        if sprint_until:
            if sprint_until.tzinfo is None:
                sprint_until = sprint_until.replace(tzinfo=tz)
            if sprint_until > now:
                speed_mult = 0.5

        secs = edge["base_distance"] * secs_per_dist * (1 - speed_mult)
        arrived = (now - start).total_seconds() >= secs

        remaining = max(0, int(secs - (now - start).total_seconds()))
        sprint_active = sprint_until and sprint_until.tzinfo is None and sprint_until > now if sprint_until else False

        if not arrived:
            cur_name = await db.fetchval("SELECT name FROM map_nodes WHERE id=$1", user["current_node"])
            target_name = await db.fetchval("SELECT name FROM map_nodes WHERE id=$1", user["travel_target"])
            path = user.get("travel_path") or []
            path_names = [target_name]
            for pid in path:
                n = await db.fetchval("SELECT name FROM map_nodes WHERE id=$1", pid)
                if n: path_names.append(n)
            route = " → ".join(path_names)

            try:
                channel = self.get_channel(int(user["travel_channel_id"])) if user["travel_channel_id"] else None
                if channel:
                    msg = await channel.fetch_message(int(user["travel_message_id"]))
                    embed = discord.Embed(title="🚶 自動導航", color=discord.Color.teal())
                    embed.add_field(name="📍 目前位置", value=cur_name or "?", inline=True)
                    embed.add_field(name="⏱️ 剩餘", value=f"{remaining} 秒 → **{target_name or '?'}**", inline=True)
                    embed.add_field(name="🗺️ 路線", value=f"**{route}**", inline=False)
                    sprint_tag = "⚡ 奔跑中！" if sprint_active else ""
                    embed.set_footer(text=sprint_tag or "移動中...")
                    await msg.edit(embed=embed)
            except:
                pass
            return

        old_node = user["current_node"]
        arrived_node_id = user["travel_target"]
        path = user.get("travel_path") or []

        await db.execute(
            "UPDATE users SET current_node=$1 WHERE discord_id=$2",
            arrived_node_id, user_id,
        )

        target_name = await db.fetchval("SELECT name FROM map_nodes WHERE id=$1", arrived_node_id)
        target_node = await db.fetchrow(
            "SELECT name, is_safe, node_type FROM map_nodes WHERE id=$1", arrived_node_id
        )

        if path:
            next_target = path[0]
            remaining_path = path[1:] if len(path) > 1 else []
            next_edge = await db.fetchrow(
                "SELECT base_distance FROM map_edges WHERE (from_node=$1 AND to_node=$2) OR (from_node=$2 AND to_node=$1)",
                arrived_node_id, next_target,
            )
            travel_secs = next_edge["base_distance"] * secs_per_dist if next_edge else 60
            await db.execute(
                "UPDATE users SET travel_target=$1, travel_path=$2, travel_start=NOW() WHERE discord_id=$3",
                next_target, remaining_path, user_id,
            )
            next_name = await db.fetchval("SELECT name FROM map_nodes WHERE id=$1", next_target)
            remaining_names = [next_name]
            for pid in remaining_path:
                n = await db.fetchval("SELECT name FROM map_nodes WHERE id=$1", pid)
                if n: remaining_names.append(n)
            route = " → ".join(remaining_names)

            try:
                channel = self.get_channel(int(user["travel_channel_id"])) if user["travel_channel_id"] else None
                if channel:
                    msg = await channel.fetch_message(int(user["travel_message_id"]))
                    embed = discord.Embed(title="🚶 自動導航", color=discord.Color.teal())
                    embed.add_field(name="📍 抵達", value=f"**{target_name}**，繼續前進", inline=True)
                    embed.add_field(name="⏱️ 剩餘路線", value=f"{route}（{travel_secs} 秒）", inline=True)
                    embed.set_footer(text="自動導航中...")
                    await msg.edit(embed=embed)
            except:
                pass
        else:
            await db.execute(
                "UPDATE users SET travel_target=NULL, travel_start=NULL, travel_path=NULL, "
                "travel_message_id=NULL, travel_channel_id=NULL WHERE discord_id=$1",
                user_id,
            )
            try:
                channel = self.get_channel(int(user["travel_channel_id"])) if user["travel_channel_id"] else None
                if channel:
                    msg = await channel.fetch_message(int(user["travel_message_id"]))
                    embed = discord.Embed(title="✅ 已抵達！", description=f"**{target_name}**", color=discord.Color.green())
                    heal_text = ""

                    if target_node and target_node["node_type"] == "temple":
                        last_pray = user.get("last_pray_date")
                        today_tz = datetime.now(tz).date()
                        if not last_pray or last_pray != today_tz:
                            view = IncenseView(user_id, target_name)
                            embed.description = f"**{target_name}**\n🕯️ 大士爺慈悲，是否領取今日 3 柱香？"
                            embed.set_footer(text="鬼王庇佑之地")
                            await msg.edit(embed=embed, view=view)
                            return
                        else:
                            heal_text = "\n🛡️ 鬼王庇佑：今日已領取香火"

                    if target_node and target_node["is_safe"] and target_node["node_type"] == "capital":
                        heal_text += "\n❤️ 主城保護：血量已恢復"
                    embed.set_footer(text=f"旅程結束{heal_text}")
                    await msg.edit(embed=embed, view=None)
            except:
                pass

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
