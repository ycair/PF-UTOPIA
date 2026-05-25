"""信仰系統: 女僕教堂打坐掛機 + 大士爺廟膜拜 buff"""
import random
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user
from src.hotconfig import game_params
from src.channel_guard import require_channel

TZ = timezone(timedelta(hours=8))
PRAY_BUFF_MINUTES = 30
PRAY_ATK_MULT = 1.5
INCENSE_PER_PRAY = 3
DAILY_INCENSE = 3

MEDITATE_LOOT_TABLE = [
    ("黏液", 1, 3, 0.4), ("羽毛", 1, 3, 0.4),
    ("肉", 1, 2, 0.35), ("羊毛", 1, 3, 0.35),
    ("骨頭", 1, 2, 0.3), ("牙齒", 1, 2, 0.25),
    ("皮革", 1, 2, 0.2), ("毒液", 1, 1, 0.15),
    ("魔石", 1, 1, 0.1), ("緞帶", 1, 1, 0.03),
]


class Faith(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="meditate_start", description="在女僕教堂開始打坐修行（離線掛機）")
    async def meditate_start(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "meditate"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            if user["meditating"]:
                await interaction.response.send_message("🔴 你已經在打坐中了！", ephemeral=True)
                return
            await db.execute(
                "UPDATE users SET meditating=TRUE, meditate_start=NOW() WHERE discord_id=$1",
                str(interaction.user.id),
            )
        await interaction.response.send_message(
            "🧘 你開始在女僕教堂打坐修行。\n"
            "打坐期間無法進行任何動作，使用 `/meditate_stop` 結束打坐領取獎勵。"
        )

    @app_commands.command(name="meditate_stop", description="結束打坐，領取掛機獎勵")
    async def meditate_stop(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "meditate"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            if not user["meditating"]:
                await interaction.response.send_message("🔴 你沒有在打坐！", ephemeral=True)
                return

            start = user["meditate_start"]
            if not start:
                await interaction.response.send_message("🔴 打坐記錄異常，請聯絡管理員。", ephemeral=True)
                return

            now = datetime.now(TZ)
            if start.tzinfo is None:
                start = start.replace(tzinfo=TZ)
            elapsed = now - start
            hours = max(elapsed.total_seconds() / 3600, 0.016)

            tuo_bi = int(hours * 60)
            items = {}
            loot_rolls = max(1, int(hours * 2))
            for _ in range(loot_rolls):
                roll = random.random()
                cum = 0
                for name, qmin, qmax, chance in MEDITATE_LOOT_TABLE:
                    cum += chance
                    if roll < cum:
                        qty = random.randint(qmin, qmax)
                        items[name] = items.get(name, 0) + qty
                        break

            yuan_exp = int(hours * 10)
            await db.execute(
                "UPDATE users SET meditating=FALSE, meditate_start=NULL, tuo_bi=tuo_bi+$1, "
                "yuan_shen_exp=yuan_shen_exp+$2 WHERE discord_id=$3",
                tuo_bi, yuan_exp, str(interaction.user.id),
            )
            for item_name, qty in items.items():
                item_row = await db.fetchrow("SELECT id FROM items WHERE name=$1", item_name)
                if item_row:
                    await db.execute(
                        "INSERT INTO inventory (user_id, item_id, quantity) VALUES ($1,$2,$3) "
                        "ON CONFLICT (user_id, item_id) DO UPDATE SET quantity=inventory.quantity+$3",
                        str(interaction.user.id), item_row["id"], qty,
                    )

            level_up = await _check_yuan_level(db, str(interaction.user.id))

        h = int(hours)
        m = int((hours - h) * 60)
        embed = discord.Embed(title="🧘 打坐結束", color=discord.Color.teal())
        embed.add_field(name="打坐時長", value=f"{h} 小時 {m} 分鐘", inline=True)
        embed.add_field(name="托幣獎勵", value=f"+{tuo_bi:,} 托幣", inline=True)
        embed.add_field(name="元神經驗", value=f"+{yuan_exp} EXP", inline=True)
        if items:
            item_str = "\n".join(f"📦 {k} ×{v}" for k, v in items.items())
            embed.add_field(name="戰利品", value=item_str, inline=False)
        if level_up:
            embed.add_field(name="🎉 元神升級", value=level_up, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pray", description="在大士爺廟膜拜（每日3柱香，滿血+30分鐘50%攻擊加成）")
    async def pray(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "pray"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return

            today = datetime.now(TZ).date()
            last_pray = user.get("last_pray_date")
            if last_pray and last_pray == today:
                current_incense = user["daily_incense"]
            else:
                current_incense = DAILY_INCENSE

            if current_incense < INCENSE_PER_PRAY:
                await interaction.response.send_message(
                    f"🔴 香火不足！每日 3 柱香，膜拜需 {INCENSE_PER_PRAY} 柱。明日再來。"
                )
                return

            await db.execute(
                "UPDATE users SET daily_incense=daily_incense-$1, last_pray_date=$2, "
                "stamina=max_stamina, current_hp=hp, atk_buff_mult=$3, atk_buff_expires=NOW()+INTERVAL'30 minutes', "
                "xiu_wei_progress=xiu_wei_progress+1 WHERE discord_id=$4",
                INCENSE_PER_PRAY, today, PRAY_ATK_MULT, str(interaction.user.id),
            )

            level_up = await _check_xiu_wei_level(db, str(interaction.user.id))

        embed = discord.Embed(title="🙏 大士爺廟膜拜", color=discord.Color.gold())
        embed.add_field(name="鬼王庇佑", value="❤️ 滿血恢復", inline=True)
        embed.add_field(name="戰鬥加持", value=f"⚔️ 攻擊力 +50%（{PRAY_BUFF_MINUTES} 分鐘）", inline=True)
        embed.add_field(name="修為", value="+1 進度", inline=True)
        embed.add_field(name="剩餘香火", value=f"{user['daily_incense'] - INCENSE_PER_PRAY} / {DAILY_INCENSE} 柱", inline=True)
        if level_up:
            embed.add_field(name="🎉 修為升級", value=level_up, inline=False)
        await interaction.response.send_message(embed=embed)


async def _check_yuan_level(db, user_id):
    user = await db.fetchrow(
        "SELECT yuan_shen_level, yuan_shen_exp FROM users WHERE discord_id=$1", user_id
    )
    level = user["yuan_shen_level"]
    exp = user["yuan_shen_exp"]
    exp_needed = (level + 1) * 50
    if exp >= exp_needed:
        await db.execute(
            "UPDATE users SET yuan_shen_level=yuan_shen_level+1, yuan_shen_exp=yuan_shen_exp-$1 WHERE discord_id=$2",
            exp_needed, user_id,
        )
        hp_bonus = (level + 2) * 5
        await db.execute(
            "UPDATE users SET hp=hp+5, max_stamina=max_stamina+5 WHERE discord_id=$1", user_id
        )
        return f"元神 Lv.{level} → Lv.{level + 1}（HP+5, 體力上限+5）"
    return None


async def _check_xiu_wei_level(db, user_id):
    user = await db.fetchrow(
        "SELECT xiu_wei_level, xiu_wei_progress FROM users WHERE discord_id=$1", user_id
    )
    level = user["xiu_wei_level"]
    prog = user["xiu_wei_progress"]
    needed = (level + 1) * 3
    if prog >= needed:
        await db.execute(
            "UPDATE users SET xiu_wei_level=xiu_wei_level+1, xiu_wei_progress=xiu_wei_progress-$1, "
            "ability_points=ability_points+1 WHERE discord_id=$2",
            needed, user_id,
        )
        return f"修為 Lv.{level} → Lv.{level + 1}（能力點 +1）"
    return None


async def setup(bot: commands.Bot):
    await bot.add_cog(Faith(bot))
