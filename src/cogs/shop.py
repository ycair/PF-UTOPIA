import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user
from src.channel_guard import require_channel
from src.hotconfig import combat_zones

ZONE_ITEM_MAP = {}


async def _get_sell_price(db, user_id, item_id):
    user = await db.fetchrow("SELECT current_node FROM users WHERE discord_id=$1", str(user_id))
    node_id = user["current_node"] if user else None
    if not node_id:
        return None, "flat", "未知位置"

    node = await db.fetchrow("SELECT name, node_type FROM map_nodes WHERE id=$1", node_id)
    in_city = node["node_type"] in IN_CITY_TYPES if node else False

    price_row = await db.fetchrow(
        "SELECT current_price, direction FROM node_prices WHERE node_id=$1 AND item_id=$2",
        node_id, item_id)
    if price_row:
        return price_row["current_price"], price_row["direction"], node["name"]

    if in_city:
        price_row = await db.fetchrow(
            "SELECT current_price, direction FROM node_prices WHERE node_id=1 AND item_id=$2",
            item_id)
        if price_row:
            return price_row["current_price"], price_row["direction"], node["name"]

    return None, "flat", node["name"] if node else "未知"


IN_CITY_TYPES = ("capital", "town", "arena", "sanctuary")


async def _get_shop_context(db, user_id):
    user = await db.fetchrow(
        "SELECT current_node FROM users WHERE discord_id=$1", str(user_id))
    node_id = user["current_node"] if user else None
    node_name = "未知"
    in_city = False
    is_temple = False
    if node_id:
        node = await db.fetchrow(
            "SELECT name, node_type FROM map_nodes WHERE id=$1", node_id)
        node_name = node["name"] if node else "未知"
        in_city = node["node_type"] in IN_CITY_TYPES if node else False
        is_temple = node["node_type"] == "temple" if node else False
    return node_id, node_name, in_city, is_temple


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
            node_id, node_name, in_city, is_temple = await _get_shop_context(db, interaction.user.id)

            main_prices = await db.fetch(
                "SELECT i.*, np.current_price AS sell_price, np.direction FROM items i "
                "JOIN node_prices np ON np.item_id=i.id AND np.node_id=1 "
                "WHERE i.item_type='material' ORDER BY i.id"
            )
            node_price_map = {}
            if node_id:
                rows = await db.fetch(
                    "SELECT item_id, current_price, direction FROM node_prices WHERE node_id=$1", node_id)
                for r in rows:
                    node_price_map[r["item_id"]] = (r["current_price"], r["direction"])

            cons = await db.fetch("SELECT * FROM items WHERE item_type='consumable' ORDER BY id")

        embed = discord.Embed(
            title=f"🏪 商店 — {node_name}",
            color=discord.Color.gold(),
        )

        mats = []
        for r in main_prices:
            d = dict(r)
            if in_city:
                price, direction = d["sell_price"], d.get("direction", "flat")
            elif node_id and d["id"] in node_price_map:
                price, direction = node_price_map[d["id"]]
            else:
                continue
            dir_icon = {"up": "🔺", "down": "🔻", "flat": "➖"}.get(direction, "➖")
            mats.append(f"{d['emoji']} **{d['name']}**  {dir_icon} {price:,} 托幣")

        if mats and category in ("all", "materials"):
            embed.add_field(name="📦 材料收購", value="\n".join(mats), inline=False)
        elif category in ("all", "materials") and not in_city:
            embed.add_field(name="📦 材料收購", value="此地不收購材料", inline=False)

        if category in ("all", "consumables"):
            price_mult = 1.0 if in_city else 1.2
            cons_lines = []
            for r in cons:
                p = int(r["buy_price"] * price_mult)
                tag = "" if in_city else f"（城外+20%）"
                cons_lines.append(f"{r['emoji']} **{r['name']}**  💰 {p:,} 托幣{tag}")
            embed.add_field(name="🧪 消耗品", value="\n".join(cons_lines), inline=False)

        embed.set_footer(
            text=f"{'🏰 城內' if in_city else '⚠️ 城外'} | /shop_buy 購買消耗品 | /shop_sell 出售材料")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shop_buy", description="購買消耗品（使用托幣）")
    @app_commands.describe(item_name="要購買的道具", quantity="購買數量")
    @app_commands.choices(item_name=[
        app_commands.Choice(name="恢復劑 100托幣", value="恢復劑"),
        app_commands.Choice(name="強效恢復劑 300托幣", value="強效恢復劑"),
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
            _, _, in_city, _ = await _get_shop_context(db, interaction.user.id)

            item = await db.fetchrow("SELECT * FROM items WHERE name=$1 AND item_type='consumable'", item_name)
            if not item:
                await interaction.response.send_message("🔴 此道具無法購買。", ephemeral=True)
                return
            price_mult = 1.0 if in_city else 1.2
            unit_price = int(item["buy_price"] * price_mult)
            total_cost = unit_price * quantity
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
        tag = "" if in_city else "（城外+20%）"
        await interaction.response.send_message(
            f"✅ 購買成功！{item['emoji']} **{item_name}** ×{quantity}（花費 {total_cost:,} 托幣）{tag}"
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

            sell_price, direction, location = await _get_sell_price(db, interaction.user.id, item["id"])
            if sell_price is None:
                await interaction.response.send_message(f"🔴 **{location}** 不收購此道具。")
                return

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
            f"　{dir_icon} 單價 {sell_price:,} 托幣 | 合計 💴 +{total_tuo_bi:,} 托幣\n"
            f"　📍 於 **{location}**"
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
            sell_price, direction, location = await _get_sell_price(db, interaction.user.id, item["id"])
            if sell_price is None:
                await interaction.response.send_message(f"🔴 **{location}** 不收購此道具。")
                return
        dir_icon = {"up": "🔺", "down": "🔻", "flat": "➖"}.get(direction, "➖")
        await interaction.response.send_message(
            f"{item['emoji']} **{item_name}**  {dir_icon} 賣價 **{sell_price:,}** 托幣\n"
            f"📍 於 **{location}**"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Shop(bot))
