import discord
from discord.ext import commands
from discord import app_commands

from src.channel_guard import require_channel


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="wyr", description="你寧可投稿（Would You Rather）")
    @app_commands.describe(question="問題", option_a="選項 A", option_b="選項 B")
    async def wyr(self, interaction: discord.Interaction, question: str, option_a: str, option_b: str):
        if not await require_channel(interaction, "wyr"):
            return
        embed = discord.Embed(
            title="🎩 你寧可...",
            description=f"**{question}**",
            color=discord.Color.orange(),
        )
        embed.add_field(name="🇦", value=option_a, inline=True)
        embed.add_field(name="🇧", value=option_b, inline=True)
        embed.set_footer(text=f"投稿者：{interaction.user.display_name} | 按 🇦 或 🇧 投票！")
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        try:
            await msg.add_reaction("🇦")
            await msg.add_reaction("🇧")
        except discord.HTTPException:
            pass

    @app_commands.command(name="event", description="查看當前進行中的活動")
    async def event(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "event"):
            return
        embed = discord.Embed(
            title="🎪 安逸烏托邦 — 活動中心",
            description="當前沒有進行中的活動。敬請期待！",
            color=discord.Color.gold(),
        )
        embed.add_field(name="常駐活動", value=(
            "🎮 數字接龍\n"
            "💰 投資交易所\n"
            "🎟 升官彩券\n"
            "🚩 烏托邦冒險"
        ), inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))
