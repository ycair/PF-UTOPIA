import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user, create_user, user_embed_fields
from src.channel_guard import require_channel

MAIN_CITY = "烏托邦主城"


class Registration(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="register", description="註冊成為安逸烏托邦的居民")
    async def register(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "register"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if user:
                await interaction.response.send_message(
                    "🔴 你已經註冊過了！使用 `/profile` 查看你的角色資料。", ephemeral=True
                )
                return
            user = await create_user(db, interaction.user.id, interaction.user.display_name)
            main = await db.fetchrow("SELECT id FROM map_nodes WHERE name=$1", MAIN_CITY)
            if main:
                await db.execute(
                    "UPDATE users SET current_node=$1 WHERE discord_id=$2",
                    main["id"], str(interaction.user.id),
                )

        embed = discord.Embed(
            title="🎉 註冊成功！歡迎來到安逸烏托邦",
            description=f"<@{interaction.user.id}> 已成為安逸烏托邦的正式居民！\n"
                        f"你的冒險即將開始...",
            color=discord.Color.gold(),
        )
        for name, value in user_embed_fields(user):
            embed.add_field(name=name, value=value, inline=True)
        embed.set_footer(text="使用 /daily 開始每日簽到！")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Registration(bot))
