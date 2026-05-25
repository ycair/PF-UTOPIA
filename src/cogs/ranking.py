import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user, compute_ability_score
from src.channel_guard import require_channel


class Ranking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="rank", description="查看排行榜")
    @app_commands.describe(category="排行類別")
    @app_commands.choices(category=[
        app_commands.Choice(name="⚔️ 戰力排行", value="power"),
        app_commands.Choice(name="🪙 安幣財富", value="wealth"),
        app_commands.Choice(name="🔥 連續簽到", value="signin"),
    ])
    async def rank(self, interaction: discord.Interaction, category: str):
        if not await require_channel(interaction, "rank"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            if category == "power":
                rows = await db.fetch(
                    "SELECT discord_id, username, attack, defense, hp FROM users ORDER BY (attack*100 + defense*50 + hp*10) DESC LIMIT 10"
                )
                embed_title = "⚔️ 戰力排行榜"
                entries = []
                for i, r in enumerate(rows, 1):
                    r = dict(r)
                    score = compute_ability_score(r["attack"], r["defense"], r["hp"])
                    entries.append(f"{_medal(i)} **{r['username']}** — {score:,} 分")

            elif category == "wealth":
                rows = await db.fetch(
                    "SELECT discord_id, username, an_bi FROM users ORDER BY an_bi DESC LIMIT 10"
                )
                embed_title = "🪙 安幣財富榜"
                entries = []
                for i, r in enumerate(rows, 1):
                    entries.append(f"{_medal(i)} **{r['username']}** — {r['an_bi']:,} 安幣")

            elif category == "signin":
                rows = await db.fetch(
                    "SELECT discord_id, username, signin_streak FROM users ORDER BY signin_streak DESC LIMIT 10"
                )
                embed_title = "🔥 連續簽到榜"
                entries = []
                for i, r in enumerate(rows, 1):
                    entries.append(f"{_medal(i)} **{r['username']}** — {r['signin_streak']} 天")

        if not entries:
            await interaction.response.send_message("📊 尚無排行資料。")
            return

        embed = discord.Embed(title=embed_title, color=discord.Color.gold())
        embed.add_field(name="排名", value="\n".join(entries), inline=False)
        await interaction.response.send_message(embed=embed)


def _medal(rank: int) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Ranking(bot))
