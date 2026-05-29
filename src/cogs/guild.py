import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user
from src.channel_guard import require_channel

ADVENTURER_RANKS = [
    (0, "見習", 0),
    (1, "銅級", 1000),
    (2, "銀級", 5000),
    (3, "金級", 15000),
    (4, "白金級", 40000),
    (5, "鑽石級", 100000),
    (6, "傳說級", 250000),
    (7, "神話級", 500000),
]


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

            score = user["attack"] * 100 + user["defense"] * 50 + user["hp"] * 10
            current_rank = user.get("adventurer_rank") or 0
            new_rank = current_rank
            rank_name = ADVENTURER_RANKS[current_rank][1]

            for i, (rid, rname, required) in enumerate(ADVENTURER_RANKS):
                if score >= required and rid > current_rank:
                    new_rank = rid
                    rank_name = rname

            if new_rank > current_rank:
                await db.execute(
                    "UPDATE users SET adventurer_rank=$1 WHERE discord_id=$2",
                    new_rank, str(interaction.user.id),
                )
                old_name = ADVENTURER_RANKS[current_rank][1]
                await interaction.response.send_message(
                    f"🎖️ 冒險者等級提升！**{old_name}** → **{rank_name}**\n"
                    f"能力評分：{score:,} 分"
                )
            else:
                next_idx = min(current_rank + 1, len(ADVENTURER_RANKS) - 1)
                next_name = ADVENTURER_RANKS[next_idx][1]
                next_req = ADVENTURER_RANKS[next_idx][2]
                await interaction.response.send_message(
                    f"🎖️ 當前等級：**{rank_name}**\n"
                    f"能力評分：{score:,} 分\n"
                    f"下一級：**{next_name}**（需 {next_req:,} 分）"
                )


async def setup(bot: commands.Bot):
    await bot.add_cog(Guild(bot))
