from datetime import timezone, timedelta, datetime

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

        current_hp = u.get("current_hp")
        max_hp = u["hp"]
        if current_hp is not None:
            embed.add_field(
                name=f"❤️ 血量",
                value=f"{max(0, current_hp):.0f}/{max_hp}",
                inline=True,
            )

        node_id = u.get("current_node")
        if node_id:
            pool = await get_pool()
            async with pool.acquire() as db:
                node = await db.fetchrow("SELECT name, is_safe, node_type FROM map_nodes WHERE id=$1", node_id)
            if node:
                location = f"📍 **{node['name']}**"
                if node["is_safe"]:
                    if node["node_type"] == "capital":
                        location += "\n🛡️ 主城保護：不受傷害"
                    elif node["node_type"] == "temple":
                        location += "\n🛡️ 鬼王庇佑：不受傷害"
                    else:
                        location += "\n🛡️ 安全區域"
                embed.add_field(name="目前位置", value=location, inline=True)

        buff_expires = u.get("atk_buff_expires")
        buff_mult = u.get("atk_buff_mult", 1.0)
        if buff_expires and buff_mult > 1.0:
            now = datetime.now(TZ_TW)
            if buff_expires.tzinfo is None:
                buff_expires = buff_expires.replace(tzinfo=TZ_TW)
            if buff_expires > now:
                remaining = buff_expires - now
                m = int(remaining.total_seconds() // 60)
                s = int(remaining.total_seconds() % 60)
                embed.add_field(
                    name="⚡ 鬼王加持",
                    value=f"攻擊力 +{int((buff_mult - 1) * 100)}%\n剩餘 {m} 分 {s} 秒",
                    inline=False,
                )

        embed.set_thumbnail(url=target.display_avatar.url)
        reg_time = u['registered_at'].astimezone(TZ_TW).strftime('%Y-%m-%d %H:%M')
        embed.set_footer(text=f"註冊於 {reg_time} (UTC+8)")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
