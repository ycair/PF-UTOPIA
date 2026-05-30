import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user, get_inventory
from src.channel_guard import require_channel


class Inventory(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="bag", description="查看你的背包")
    async def bag(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "bag"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先使用 `/register` 註冊！", ephemeral=True)
                return
            items = await get_inventory(db, interaction.user.id)
            if not items:
                await interaction.response.send_message("🎒 你的背包空空如也！去 `/explore` 打怪收集材料吧。")
                return

            materials = [r for r in items if r["item_type"] == "material"]
            consumables = [r for r in items if r["item_type"] == "consumable"]

        embed = discord.Embed(
            title=f"🎒 {interaction.user.display_name} 的背包",
            color=discord.Color.teal(),
        )

        def build_lines(rows):
            lines = []
            for r in rows:
                emoji = r["emoji"]
                name = r["name"]
                qty = r["quantity"]
                if r["item_type"] == "material" and r.get("sell_price"):
                    direction_icon = {"up": "🔺", "down": "🔻", "flat": "➖"}.get(r["direction"], "➖")
                    lines.append(f"{emoji} {name} ×{qty}  {direction_icon} 賣價 {r['sell_price']:,} 托幣")
                elif r["item_type"] == "consumable":
                    lines.append(f"{emoji} {name} ×{qty}  買價 {r['buy_price']:,} 托幣")
                else:
                    lines.append(f"{emoji} {name} ×{qty}")
            return "\n".join(lines) if lines else "（空）"

        embed.add_field(name="📦 材料", value=build_lines(materials), inline=False)
        embed.add_field(name="🧪 消耗品", value=build_lines(consumables), inline=False)
        embed.set_footer(text="材料賣商店換托幣 / 消耗品用 /use 使用")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="use", description="使用消耗品道具")
    @app_commands.describe(item_name="要使用的道具名稱", quantity="使用數量（預設1）")
    @app_commands.choices(item_name=[
        app_commands.Choice(name="恢復劑 (+50體力 +50HP)", value="恢復劑"),
        app_commands.Choice(name="強效恢復劑 (+150體力 +150HP)", value="強效恢復劑"),
        app_commands.Choice(name="糖果 (供奉精靈用)", value="糖果"),
        app_commands.Choice(name="轉法輪 (增加修為)", value="轉法輪"),
    ])
    async def use_item(self, interaction: discord.Interaction, item_name: str, quantity: int = 1):
        if not await require_channel(interaction, "use"):
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

            item = await db.fetchrow("SELECT * FROM items WHERE name=$1", item_name)
            if not item:
                await interaction.response.send_message("🔴 找不到該道具。", ephemeral=True)
                return

            inv = await db.fetchrow(
                "SELECT quantity FROM inventory WHERE user_id=$1 AND item_id=$2",
                str(interaction.user.id), item["id"],
            )
            if not inv or inv["quantity"] < quantity:
                await interaction.response.send_message(
                    f"🔴 背包不足！需要 {quantity} 個 {item_name}，當前 {inv['quantity'] if inv else 0} 個。", ephemeral=True
                )
                return

            await db.execute(
                "UPDATE inventory SET quantity=quantity-$1 WHERE user_id=$2 AND item_id=$3",
                quantity, str(interaction.user.id), item["id"],
            )
            await db.execute(
                "DELETE FROM inventory WHERE user_id=$1 AND item_id=$2 AND quantity <= 0",
                str(interaction.user.id), item["id"],
            )

            effect_msg = ""
            if item_name == "恢復劑":
                await db.execute(
                    "UPDATE users SET stamina=LEAST(stamina+$1, max_stamina), "
                    "current_hp=LEAST(current_hp+$1, hp) WHERE discord_id=$2",
                    50 * quantity, str(interaction.user.id),
                )
                effect_msg = f"體力 +{50*quantity}、HP +{50*quantity}！"
            elif item_name == "強效恢復劑":
                await db.execute(
                    "UPDATE users SET stamina=LEAST(stamina+$1, max_stamina), "
                    "current_hp=LEAST(current_hp+$1, hp) WHERE discord_id=$2",
                    150 * quantity, str(interaction.user.id),
                )
                effect_msg = f"體力 +{150*quantity}、HP +{150*quantity}！"
            elif item_name == "糖果":
                await db.execute(
                    "UPDATE users SET candy=candy+$1 WHERE discord_id=$2",
                    quantity, str(interaction.user.id),
                )
                effect_msg = f"糖果 +{quantity}！"
            elif item_name == "轉法輪":
                await db.execute(
                    "UPDATE users SET xiu_wei_progress=xiu_wei_progress+$1, "
                    "yuan_shen_exp=yuan_shen_exp+$2 WHERE discord_id=$3",
                    3 * quantity, 10 * quantity, str(interaction.user.id),
                )
                from src.cogs.faith import _check_xiu_wei_level, _check_yuan_level
                xiu_up = await _check_xiu_wei_level(db, str(interaction.user.id))
                yuan_up = await _check_yuan_level(db, str(interaction.user.id))
                parts = ["元神 EXP +10", "修為進度 +3"]
                if yuan_up: parts.append(f"🎉 {yuan_up}")
                if xiu_up: parts.append(f"🎉 {xiu_up}")
                effect_msg = "、".join(parts)

        await interaction.response.send_message(f"✅ 使用 {item['emoji']} **{item_name}** — {effect_msg}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Inventory(bot))
