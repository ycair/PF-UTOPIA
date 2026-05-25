import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user
from src.channel_guard import require_channel


class Shop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="shop", description="瀏覽商店商品")
    @app_commands.describe(category="商品類別")
    @app_commands.choices(category=[
        app_commands.Choice(name="全部", value="all"),
        app_commands.Choice(name="材料（賣價浮動）", value="materials"),
        app_commands.Choice(name="消耗品（固定價格）", value="consumables"),
    ])
    async def shop(self, interaction: discord.Interaction, category: str = "all"):
        if not await require_channel(interaction, "shop"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            query = "SELECT i.*, COALESCE(sp.current_price, i.base_price) AS sell_price, COALESCE(sp.direction, 'flat') AS direction FROM items i LEFT JOIN shop_sell_prices sp ON sp.item_id = i.id"
            if category == "materials":
                query += " WHERE i.item_type='material'"
            elif category == "consumables":
                query += " WHERE i.item_type='consumable'"
            query += " ORDER BY i.item_type, i.id"
            rows = await db.fetch(query)

        embed = discord.Embed(title="🏪 安逸商店", color=discord.Color.gold())

        mats, cons = [], []
        for r in rows:
            d = dict(r)
            if d["item_type"] == "material":
                dir_icon = {"up": "🔺", "down": "🔻", "flat": "➖"}.get(d["direction"], "➖")
                mats.append(f"{d['emoji']} **{d['name']}**  {dir_icon} 賣價 {d['sell_price']:,} 托幣\n　{d['description']}")
            else:
                cons.append(f"{d['emoji']} **{d['name']}**  💰 {d['buy_price']:,} 托幣\n　{d['description']}")
        if mats and category in ("all", "materials"):
            embed.add_field(name="📦 材料（賣給商店換托幣，價格浮動）", value="\n".join(mats), inline=False)
        if cons and category in ("all", "consumables"):
            embed.add_field(name="🧪 消耗品（用托幣購買，固定價格）", value="\n".join(cons), inline=False)
        embed.set_footer(text="/shop_buy 購買消耗品 | /shop_sell 出售材料")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shop_buy", description="購買消耗品（使用托幣）")
    @app_commands.describe(item_name="要購買的道具", quantity="購買數量")
    @app_commands.choices(item_name=[
        app_commands.Choice(name="體力恢復劑 100托幣", value="體力恢復劑"),
        app_commands.Choice(name="強效體力恢復劑 300托幣", value="強效體力恢復劑"),
        app_commands.Choice(name="線香 50托幣", value="線香"),
        app_commands.Choice(name="糖果 30托幣", value="糖果"),
        app_commands.Choice(name="轉法輪 500托幣", value="轉法輪"),
    ])
    async def shop_buy(self, interaction: discord.Interaction, item_name: str, quantity: int = 1):
        if not await require_channel(interaction, "shop_buy"):
            return
        if quantity < 1:
            await interaction.response.send_message("🔴 購買數量需大於 0。", ephemeral=True)
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            item = await db.fetchrow("SELECT * FROM items WHERE name=$1 AND item_type='consumable'", item_name)
            if not item:
                await interaction.response.send_message("🔴 此道具無法購買。", ephemeral=True)
                return
            total_cost = item["buy_price"] * quantity
            if user["tuo_bi"] < total_cost:
                await interaction.response.send_message(
                    f"🔴 托幣不足！需要 {total_cost:,} 元，當前 {user['tuo_bi']:,} 元。"
                )
                return
            await db.execute(
                "UPDATE users SET tuo_bi=tuo_bi-$1 WHERE discord_id=$2",
                total_cost, str(interaction.user.id),
            )
            await db.execute(
                "INSERT INTO inventory (user_id, item_id, quantity) VALUES ($1,$2,$3) "
                "ON CONFLICT (user_id, item_id) DO UPDATE SET quantity=inventory.quantity+$3",
                str(interaction.user.id), item["id"], quantity,
            )
        await interaction.response.send_message(
            f"✅ 購買成功！{item['emoji']} **{item_name}** ×{quantity}（花費 {total_cost:,} 托幣）"
        )

    @app_commands.command(name="shop_sell", description="出售材料給商店（獲得托幣，價格浮動）")
    @app_commands.describe(item_name="要出售的材料", quantity="出售數量")
    @app_commands.choices(item_name=[
        app_commands.Choice(name="黏液", value="黏液"),
        app_commands.Choice(name="羽毛", value="羽毛"),
        app_commands.Choice(name="肉", value="肉"),
        app_commands.Choice(name="羊毛", value="羊毛"),
        app_commands.Choice(name="骨頭", value="骨頭"),
        app_commands.Choice(name="牙齒", value="牙齒"),
        app_commands.Choice(name="皮革", value="皮革"),
        app_commands.Choice(name="緞帶", value="緞帶"),
        app_commands.Choice(name="毒液", value="毒液"),
        app_commands.Choice(name="魔石", value="魔石"),
    ])
    async def shop_sell(self, interaction: discord.Interaction, item_name: str, quantity: int = 1):
        if not await require_channel(interaction, "shop_sell"):
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
            item = await db.fetchrow("SELECT * FROM items WHERE name=$1 AND item_type='material'", item_name)
            if not item:
                await interaction.response.send_message("🔴 此道具無法出售。", ephemeral=True)
                return
            inv = await db.fetchrow(
                "SELECT quantity FROM inventory WHERE user_id=$1 AND item_id=$2",
                str(interaction.user.id), item["id"],
            )
            if not inv or inv["quantity"] < quantity:
                await interaction.response.send_message(
                    f"🔴 背包中沒有足夠的 {item_name}！當前 {inv['quantity'] if inv else 0} 個。"
                )
                return

            price_row = await db.fetchrow(
                "SELECT current_price, direction FROM shop_sell_prices WHERE item_id=$1", item["id"],
            )
            sell_price = price_row["current_price"] if price_row else item["base_price"]
            direction = price_row["direction"] if price_row else "flat"

            total_tuo_bi = sell_price * quantity
            await db.execute(
                "UPDATE inventory SET quantity=quantity-$1 WHERE user_id=$2 AND item_id=$3",
                quantity, str(interaction.user.id), item["id"],
            )
            await db.execute(
                "DELETE FROM inventory WHERE user_id=$1 AND item_id=$2 AND quantity<=0",
                str(interaction.user.id), item["id"],
            )
            await db.execute(
                "UPDATE users SET tuo_bi=tuo_bi+$1 WHERE discord_id=$2",
                total_tuo_bi, str(interaction.user.id),
            )

        dir_icon = {"up": "🔺", "down": "🔻", "flat": "➖"}.get(direction, "➖")
        await interaction.response.send_message(
            f"✅ 出售成功！{item['emoji']} **{item_name}** ×{quantity}\n"
            f"　{dir_icon} 單價 {sell_price:,} 托幣 | 合計 💴 +{total_tuo_bi:,} 托幣"
        )

    @app_commands.command(name="shop_price", description="查詢材料當前賣價（不賣出）")
    @app_commands.describe(item_name="要查詢的材料")
    @app_commands.choices(item_name=[
        app_commands.Choice(name="黏液", value="黏液"),
        app_commands.Choice(name="羽毛", value="羽毛"),
        app_commands.Choice(name="肉", value="肉"),
        app_commands.Choice(name="羊毛", value="羊毛"),
        app_commands.Choice(name="骨頭", value="骨頭"),
        app_commands.Choice(name="牙齒", value="牙齒"),
        app_commands.Choice(name="皮革", value="皮革"),
        app_commands.Choice(name="緞帶", value="緞帶"),
        app_commands.Choice(name="毒液", value="毒液"),
        app_commands.Choice(name="魔石", value="魔石"),
    ])
    async def shop_price(self, interaction: discord.Interaction, item_name: str):
        if not await require_channel(interaction, "shop_sell"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            item = await db.fetchrow("SELECT * FROM items WHERE name=$1 AND item_type='material'", item_name)
            if not item:
                await interaction.response.send_message("🔴 此道具無法出售。", ephemeral=True)
                return
            price_row = await db.fetchrow(
                "SELECT current_price, direction FROM shop_sell_prices WHERE item_id=$1", item["id"],
            )
            sell_price = price_row["current_price"] if price_row else item["base_price"]
            direction = price_row["direction"] if price_row else "flat"
        dir_icon = {"up": "🔺", "down": "🔻", "flat": "➖"}.get(direction, "➖")
        await interaction.response.send_message(
            f"{item['emoji']} **{item_name}**  {dir_icon} 當前賣價 **{sell_price:,}** 托幣"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Shop(bot))
