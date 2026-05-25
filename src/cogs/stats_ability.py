import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user
from src.channel_guard import require_channel


class StatsAbility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ability", description="分配能力點數提升屬性")
    @app_commands.describe(stat="要提升的屬性", amount="分配點數")
    @app_commands.choices(stat=[
        app_commands.Choice(name="⚔️ 攻擊", value="attack"),
        app_commands.Choice(name="🛡️ 防禦", value="defense"),
        app_commands.Choice(name="❤️ 血量", value="hp"),
    ])
    async def ability(self, interaction: discord.Interaction, stat: str, amount: int):
        if not await require_channel(interaction, "ability"):
            return
        if amount < 1:
            await interaction.response.send_message("🔴 分配點數必須大於 0。", ephemeral=True)
            return

        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            if user["ability_points"] < amount:
                await interaction.response.send_message(
                    f"🔴 能力點不足！當前 {user['ability_points']} 點，需要 {amount} 點。",
                    ephemeral=True,
                )
                return

            await db.execute(
                f"UPDATE users SET {stat}={stat}+$1, ability_points=ability_points-$1 WHERE discord_id=$2",
                amount, str(interaction.user.id),
            )

        stat_name = {"attack": "⚔️ 攻擊", "defense": "🛡️ 防禦", "hp": "❤️ 血量"}[stat]
        embed = discord.Embed(
            title="🧬 能力分配成功",
            description=f"**{interaction.user.display_name}** 提升了 {stat_name}！",
            color=discord.Color.green(),
        )
        embed.add_field(name="分配", value=f"{stat_name} +{amount}", inline=True)
        embed.add_field(name="剩餘能力點", value=f"{user['ability_points'] - amount} 點", inline=True)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(StatsAbility(bot))
