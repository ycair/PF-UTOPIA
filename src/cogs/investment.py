import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user
from src.channel_guard import require_channel


class Investment(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="market", description="查看股市行情")
    async def market(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "market"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            stocks = await db.fetch("SELECT * FROM stocks ORDER BY id")
            if not stocks:
                await interaction.response.send_message("📊 尚無股票資料。")
                return

        embed = discord.Embed(title="🏦 投資交易所 — 行情報價", color=discord.Color.teal())
        for s in stocks:
            s = dict(s)
            history = await db.fetch(
                "SELECT price FROM stock_history WHERE stock_id=$1 ORDER BY recorded_at DESC LIMIT 2",
                s["id"],
            )
            if len(history) >= 2:
                old_price = history[1]["price"]
                change_pct = (s["current_price"] - old_price) / old_price * 100
                icon = "🔴" if change_pct > 0 else ("🟢" if change_pct < 0 else "➖")
                embed.add_field(
                    name=f"{s['emoji']} {s['name']}",
                    value=f"💰 {s['current_price']:,} 托幣\n{icon} {change_pct:+.2f}%",
                    inline=True,
                )
            else:
                embed.add_field(
                    name=f"{s['emoji']} {s['name']}",
                    value=f"💰 {s['current_price']:,} 托幣",
                    inline=True,
                )
        embed.set_footer(text="/invest_buy 買入 | /invest_sell 賣出 | /invest_portfolio 持倉")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="invest_buy", description="購買股票（使用托幣）")
    @app_commands.describe(stock="選擇股票", quantity="購買股數")
    @app_commands.choices(stock=[
        app_commands.Choice(name="青銅烏龜", value="bronze_turtle"),
        app_commands.Choice(name="白銀烏龜", value="silver_turtle"),
        app_commands.Choice(name="黃金烏龜", value="gold_turtle"),
        app_commands.Choice(name="鑽石烏龜", value="diamond_turtle"),
        app_commands.Choice(name="石頭烏龜", value="stone_turtle"),
        app_commands.Choice(name="紅寶石烏龜", value="ruby_turtle"),
    ])
    async def invest_buy(self, interaction: discord.Interaction, stock: str, quantity: int = 1):
        if not await require_channel(interaction, "invest_buy"):
            return
        if quantity < 1:
            await interaction.response.send_message("🔴 數量需大於 0。", ephemeral=True)
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            s = await db.fetchrow("SELECT * FROM stocks WHERE code=$1", stock)
            if not s:
                await interaction.response.send_message("🔴 未知股票。", ephemeral=True)
                return
            total_cost = s["current_price"] * quantity
            if user["tuo_bi"] < total_cost:
                await interaction.response.send_message(
                    f"🔴 托幣不足！需要 {total_cost:,} 元，當前 {user['tuo_bi']:,} 元。"
                )
                return

            await db.execute(
                "UPDATE users SET tuo_bi=tuo_bi-$1 WHERE discord_id=$2",
                total_cost, str(interaction.user.id),
            )

            holding = await db.fetchrow(
                "SELECT * FROM user_stocks WHERE user_id=$1 AND stock_id=$2",
                str(interaction.user.id), s["id"],
            )
            if holding:
                new_qty = holding["quantity"] + quantity
                new_avg = int((holding["avg_cost"] * holding["quantity"] + total_cost) / new_qty)
                await db.execute(
                    "UPDATE user_stocks SET quantity=$1, avg_cost=$2 WHERE user_id=$3 AND stock_id=$4",
                    new_qty, new_avg, str(interaction.user.id), s["id"],
                )
            else:
                await db.execute(
                    "INSERT INTO user_stocks (user_id, stock_id, quantity, avg_cost) VALUES ($1,$2,$3,$4)",
                    str(interaction.user.id), s["id"], quantity, s["current_price"],
                )

        await interaction.response.send_message(
            f"✅ 買入成功！{s['emoji']} **{s['name']}** ×{quantity} 股\n"
            f"　單價 {s['current_price']:,} 托幣 | 合計 💴 -{total_cost:,} 托幣"
        )

    @app_commands.command(name="invest_sell", description="賣出股票（獲得托幣）")
    @app_commands.describe(stock="選擇股票", quantity="賣出股數")
    @app_commands.choices(stock=[
        app_commands.Choice(name="青銅烏龜", value="bronze_turtle"),
        app_commands.Choice(name="白銀烏龜", value="silver_turtle"),
        app_commands.Choice(name="黃金烏龜", value="gold_turtle"),
        app_commands.Choice(name="鑽石烏龜", value="diamond_turtle"),
        app_commands.Choice(name="石頭烏龜", value="stone_turtle"),
        app_commands.Choice(name="紅寶石烏龜", value="ruby_turtle"),
    ])
    async def invest_sell(self, interaction: discord.Interaction, stock: str, quantity: int = 1):
        if not await require_channel(interaction, "invest_sell"):
            return
        if quantity < 1:
            await interaction.response.send_message("🔴 數量需大於 0。", ephemeral=True)
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            s = await db.fetchrow("SELECT * FROM stocks WHERE code=$1", stock)
            holding = await db.fetchrow(
                "SELECT * FROM user_stocks WHERE user_id=$1 AND stock_id=$2",
                str(interaction.user.id), s["id"],
            )
            if not holding or holding["quantity"] < quantity:
                await interaction.response.send_message(
                    f"🔴 持股不足！當前 {holding['quantity'] if holding else 0} 股。"
                )
                return

            total_revenue = s["current_price"] * quantity
            profit = (s["current_price"] - holding["avg_cost"]) * quantity

            await db.execute(
                "UPDATE users SET tuo_bi=tuo_bi+$1 WHERE discord_id=$2",
                total_revenue, str(interaction.user.id),
            )
            new_qty = holding["quantity"] - quantity
            if new_qty <= 0:
                await db.execute(
                    "DELETE FROM user_stocks WHERE user_id=$1 AND stock_id=$2",
                    str(interaction.user.id), s["id"],
                )
            else:
                await db.execute(
                    "UPDATE user_stocks SET quantity=$1 WHERE user_id=$2 AND stock_id=$3",
                    new_qty, str(interaction.user.id), s["id"],
                )

        pnl_icon = "📈" if profit > 0 else ("📉" if profit < 0 else "➖")
        await interaction.response.send_message(
            f"✅ 賣出成功！{s['emoji']} **{s['name']}** ×{quantity} 股\n"
            f"　單價 {s['current_price']:,} 托幣 | 合計 💴 +{total_revenue:,} 托幣\n"
            f"　{pnl_icon} 損益 {profit:+,} 托幣"
        )

    @app_commands.command(name="invest_portfolio", description="查看你的投資組合")
    async def invest_portfolio(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "invest_portfolio"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return

            holdings = await db.fetch("""
                SELECT s.name, s.emoji, s.current_price, us.quantity, us.avg_cost
                FROM user_stocks us JOIN stocks s ON s.id = us.stock_id
                WHERE us.user_id=$1 AND us.quantity > 0
            """, str(interaction.user.id))

        if not holdings:
            await interaction.response.send_message("📊 你還沒有任何持股。使用 `/invest_buy` 開始投資！")
            return

        embed = discord.Embed(
            title=f"📊 {interaction.user.display_name} 的投資組合",
            color=discord.Color.teal(),
        )
        total_value = 0
        total_cost = 0
        for h in holdings:
            h = dict(h)
            current_val = h["current_price"] * h["quantity"]
            cost_val = h["avg_cost"] * h["quantity"]
            total_value += current_val
            total_cost += cost_val
            pnl = current_val - cost_val
            pnl_pct = (pnl / cost_val * 100) if cost_val > 0 else 0
            icon = "📈" if pnl > 0 else ("📉" if pnl < 0 else "➖")
            embed.add_field(
                name=f"{h['emoji']} {h['name']}",
                value=f"持股：{h['quantity']} 股\n成本：{cost_val:,} / 現值：{current_val:,}\n{icon} {pnl:+,} ({pnl_pct:+.1f}%)",
                inline=False,
            )

        total_pnl = total_value - total_cost
        embed.add_field(
            name="總計",
            value=f"總成本：{total_cost:,} 托幣\n總現值：{total_value:,} 托幣\n總損益：{total_pnl:+,} 托幣",
            inline=False,
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Investment(bot))
