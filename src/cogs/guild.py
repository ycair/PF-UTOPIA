import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user
from src.channel_guard import require_channel

TIERS = ["瓷", "鐵", "銀", "金", "白金", "秘銀", "精金"]
SUB = ["I", "II", "III", "IV", "V"]


def rank_name(level):
    if level >= 35:
        return "精金 V"
    tier = level // 5
    sub = level % 5
    return f"{TIERS[tier]} {SUB[sub]}"


def rank_exp_needed(level):
    return (level + 1) * 50


class Guild(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="quests", description="查看冒險者公會任務板")
    async def quests(self, interaction: discord.Interaction):
        pool = await get_pool()
        async with pool.acquire() as db:
            node = await db.fetchrow("SELECT name FROM map_nodes WHERE id=$1",
                (await db.fetchrow("SELECT current_node FROM users WHERE discord_id=$1", str(interaction.user.id)) or {}).get("current_node"))
            if not node or node["name"] != "冒險者公會":
                await interaction.response.send_message("🔴 請先到 **冒險者公會** 查看任務板！", ephemeral=True)
                return

        embed = discord.Embed(
            title="📋 冒險者公會 — 任務板",
            description="當前暫無可用任務。\n\n🤖 AI Game Master 上線後將動態派發：\n• 討伐任務\n• 收集任務\n• 探索任務\n• 護送任務",
            color=discord.Color.teal(),
        )
        embed.set_footer(text="敬請期待 AI GM 系統上線")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rank_certify", description="在冒險者公會認證你的冒險者等級")
    async def rank_certify(self, interaction: discord.Interaction):
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return

            node = await db.fetchrow("SELECT name FROM map_nodes WHERE id=$1", user.get("current_node"))
            if not node or node["name"] != "冒險者公會":
                await interaction.response.send_message("🔴 請先到 **冒險者公會** 認證！", ephemeral=True)
                return

            current = user.get("adventurer_rank") or 0
            exp = user.get("adventurer_exp") or 0
            new_level = current
            while new_level < 35:
                need = rank_exp_needed(new_level)
                if exp < need:
                    break
                exp -= need
                new_level += 1

            if new_level > current:
                await db.execute(
                    "UPDATE users SET adventurer_rank=$1, adventurer_exp=$2 WHERE discord_id=$3",
                    new_level, exp, str(interaction.user.id),
                )
                await interaction.response.send_message(
                    f"🎖️ 冒險者等級提升！**{rank_name(current)}** → **{rank_name(new_level)}**"
                )
            else:
                need = rank_exp_needed(current)
                await interaction.response.send_message(
                    f"🎖️ 當前等級：**{rank_name(current)}**\n"
                    f"EXP：{exp} / {need}\n"
                    f"戰力評分：{user['attack']*100+user['defense']*50+user['hp']*10:,} 分"
                )


async def setup(bot: commands.Bot):
    await bot.add_cog(Guild(bot))
