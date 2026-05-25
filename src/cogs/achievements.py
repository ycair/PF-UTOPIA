import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user
from src.channel_guard import require_channel


class Achievements(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="achievements", description="查看成就與進度")
    async def achievements(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "achievements"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return

            all_achievements = await db.fetch("SELECT * FROM achievements ORDER BY category, id")
            user_achievements = await db.fetch(
                "SELECT achievement_id FROM user_achievements WHERE user_id=$1",
                str(interaction.user.id),
            )
            unlocked_ids = {r["achievement_id"] for r in user_achievements}

        embed = discord.Embed(
            title=f"🏆 {interaction.user.display_name} 的成就",
            description=f"已解鎖：{len(unlocked_ids)} / {len(all_achievements)}",
            color=discord.Color.gold(),
        )

        categories = {}
        for a in all_achievements:
            a = dict(a)
            cat = a["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(a)

        cat_names = {
            "general": "基本", "daily": "簽到", "combat": "戰鬥",
            "economy": "經濟", "investment": "投資", "pet": "寵物", "lottery": "彩券",
        }
        for cat, achievements_list in categories.items():
            lines = []
            for a in achievements_list:
                icon = "✅" if a["id"] in unlocked_ids else "⬜"
                lines.append(f"{icon} **{a['name']}** — {a['description']}")
            embed.add_field(name=cat_names.get(cat, cat), value="\n".join(lines), inline=False)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Achievements(bot))
