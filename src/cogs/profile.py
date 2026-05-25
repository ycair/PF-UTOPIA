from datetime import timezone, timedelta

import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user, user_embed_fields
from src.channel_guard import require_channel

TZ_TW = timezone(timedelta(hours=8))


class Profile(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="profile", description="查看你或其他玩家的角色資料")
    @app_commands.describe(user="要查看的玩家（留空則查看自己）")
    async def profile(self, interaction: discord.Interaction, user: discord.Member | None = None):
        if not await require_channel(interaction, "profile"):
            return
        target = user or interaction.user
        pool = await get_pool()
        async with pool.acquire() as db:
            u = await get_user(db, target.id)
            if not u:
                if target == interaction.user:
                    await interaction.response.send_message(
                        "🔴 你還沒有註冊！使用 `/register` 開始冒險。", ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f"🔴 {target.display_name} 還沒有註冊。", ephemeral=True
                    )
                return

        embed = discord.Embed(
            title=f"📊 {target.display_name} 的角色資料",
            color=discord.Color.blue(),
        )
        for name, value in user_embed_fields(u):
            embed.add_field(name=name, value=value, inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        reg_time = u['registered_at'].astimezone(TZ_TW).strftime('%Y-%m-%d %H:%M')
        embed.set_footer(text=f"註冊於 {reg_time} (UTC+8)")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
