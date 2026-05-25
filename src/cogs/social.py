import random
import discord
from discord.ext import commands
from discord import app_commands

from src.channel_guard import require_channel

SOCIAL_RESPONSES = {
    "hug": [
        "給了 {target} 一個溫暖的擁抱！🤗",
        "緊緊抱住了 {target}！",
        "和 {target} 來了個大抱抱！",
    ],
    "kiss": [
        "輕輕吻了 {target} 一下！😘",
        "給了 {target} 一個甜蜜的吻！💋",
    ],
    "pat": [
        "溫柔地摸了摸 {target} 的頭！",
        "拍拍 {target} 的頭～好乖好乖～",
    ],
    "slap": [
        "毫不留情地打了 {target} 一巴掌！👋",
        "啪！{target} 的臉頰紅了...",
    ],
    "kill": [
        "🔪 假裝殺死了 {target}！但其實是假的啦～",
        "對 {target} 使用了致命一擊！（效果拔群但沒有人受傷）",
    ],
    "wink": [
        "對 {target} 眨了眨眼！😉",
        "向 {target} 拋了個媚眼～✨",
    ],
}


class Social(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _social_action(self, interaction: discord.Interaction, target: discord.Member, action: str, gif_type: str | None = None):
        msgs = SOCIAL_RESPONSES[action]
        msg = random.choice(msgs).format(target=target.display_name)
        embed = discord.Embed(
            description=f"**{interaction.user.display_name}** {msg}",
            color=discord.Color.pink(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="hug", description="擁抱某人")
    async def hug(self, interaction: discord.Interaction, user: discord.Member):
        await self._social_action(interaction, user, "hug")

    @app_commands.command(name="kiss", description="親吻某人")
    async def kiss(self, interaction: discord.Interaction, user: discord.Member):
        await self._social_action(interaction, user, "kiss")

    @app_commands.command(name="pat", description="摸某人的頭")
    async def pat(self, interaction: discord.Interaction, user: discord.Member):
        await self._social_action(interaction, user, "pat")

    @app_commands.command(name="slap", description="打某人巴掌")
    async def slap(self, interaction: discord.Interaction, user: discord.Member):
        await self._social_action(interaction, user, "slap")

    @app_commands.command(name="kill", description="假裝殺死某人")
    async def kill(self, interaction: discord.Interaction, user: discord.Member):
        await self._social_action(interaction, user, "kill")

    @app_commands.command(name="wink", description="對某人眨眼")
    async def wink(self, interaction: discord.Interaction, user: discord.Member):
        await self._social_action(interaction, user, "wink")


async def setup(bot: commands.Bot):
    await bot.add_cog(Social(bot))
