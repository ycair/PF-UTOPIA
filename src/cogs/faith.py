import random
import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user
from src.hotconfig import game_params
from src.channel_guard import require_channel


class Faith(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="pray", description="膜拜教堂，消耗線香獲得修為")
    async def pray(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "pray"):
            return
        cost = await game_params.pray_cost_xian_xiang or 1
        base_xiu_wei = await game_params.pray_base_xiu_wei or 3
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            if user["xian_xiang"] < cost:
                await interaction.response.send_message(
                    "🔴 線香不夠，可以前往副本賺取戰利品或在商店購買。"
                )
                return

            await db.execute(
                "UPDATE users SET xian_xiang=xian_xiang-$1 WHERE discord_id=$2",
                cost, str(interaction.user.id),
            )

            bonus = random.randint(1, 5)
            total_xiu_wei = base_xiu_wei + bonus
            await db.execute(
                "UPDATE users SET xiu_wei=xiu_wei+$1 WHERE discord_id=$2",
                total_xiu_wei, str(interaction.user.id),
            )

        embed = discord.Embed(
            title="⛪ 膜拜教堂",
            description=f"**{interaction.user.display_name}** 虔誠膜拜...",
            color=discord.Color.gold(),
        )
        embed.add_field(name="基礎修為", value=f"+{base_xiu_wei} 點", inline=True)
        embed.add_field(name="隨機加成", value=f"+{bonus} 點", inline=True)
        embed.add_field(name="合計", value=f"✨ 修為 +{total_xiu_wei} 點", inline=False)
        embed.set_footer(text=f"剩餘線香：{user['xian_xiang'] - 1} 根")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="meditate", description="坐禪修行，回復修為")
    async def meditate(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "meditate"):
            return
        regen = await game_params.meditate_xiu_wei_regen or 5
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            if user["xiu_wei"] >= 50:
                await interaction.response.send_message("🔴 你修為已滿，無需回復。")
                return

            await db.execute(
                "UPDATE users SET xiu_wei=LEAST(xiu_wei+$1, 50) WHERE discord_id=$2",
                regen, str(interaction.user.id),
            )

            new_xiu_wei = min(user["xiu_wei"] + regen, 50)
        embed = discord.Embed(
            title="🧘 坐禪修行",
            description=f"**{interaction.user.display_name}** 靜心打坐中...",
            color=discord.Color.teal(),
        )
        embed.add_field(name="回復修為", value=f"+{regen} 點", inline=True)
        embed.add_field(name="當前修為", value=f"{new_xiu_wei} / 50", inline=True)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Faith(bot))
