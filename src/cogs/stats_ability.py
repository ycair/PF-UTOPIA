import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone, timedelta

from src.database import get_pool, get_user
from src.hotconfig import game_params

TZ = timezone(timedelta(hours=8))
DEFAULT_ATK = 10
DEFAULT_DEF = 5
DEFAULT_HP = 100
RESET_COST = 500


class StatsAbility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ability", description="分配能力點數提升屬性（無頻道限制）")
    @app_commands.describe(stat="要提升的屬性", amount="分配點數")
    @app_commands.choices(stat=[
        app_commands.Choice(name="⚔️ 攻擊", value="attack"),
        app_commands.Choice(name="🛡️ 防禦", value="defense"),
        app_commands.Choice(name="❤️ 血量", value="hp"),
    ])
    async def ability(self, interaction: discord.Interaction, stat: str, amount: int):
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
        embed = discord.Embed(title="🧬 能力分配成功", color=discord.Color.green())
        embed.add_field(name="分配", value=f"{stat_name} +{amount}", inline=True)
        embed.add_field(name="剩餘能力點", value=f"{user['ability_points'] - amount} 點", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ability_reset", description="重置能力點（500安幣，每週一次）")
    async def ability_reset(self, interaction: discord.Interaction):
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            if user["an_bi"] < RESET_COST:
                await interaction.response.send_message(
                    f"🔴 安幣不足！需要 {RESET_COST} 元，當前 {user['an_bi']:,} 元。"
                )
                return

            last_reset = user.get("ability_reset_at")
            if last_reset:
                if last_reset.tzinfo is None:
                    last_reset = last_reset.replace(tzinfo=TZ)
                week_ago = datetime.now(TZ) - timedelta(days=7)
                if last_reset > week_ago:
                    next_reset = last_reset + timedelta(days=7)
                    await interaction.response.send_message(
                        f"🔴 每週只能重置一次！下次可用：{next_reset.strftime('%Y-%m-%d %H:%M')}"
                    )
                    return

            allocated_atk = user["attack"] - DEFAULT_ATK
            allocated_def = user["defense"] - DEFAULT_DEF
            allocated_hp = user["hp"] - DEFAULT_HP
            refund = allocated_atk + allocated_def + allocated_hp

            await db.execute(
                "UPDATE users SET attack=$1, defense=$2, hp=$3, ability_points=ability_points+$4, "
                "an_bi=an_bi-$5, ability_reset_at=NOW() WHERE discord_id=$6",
                DEFAULT_ATK, DEFAULT_DEF, DEFAULT_HP, refund, RESET_COST, str(interaction.user.id),
            )

        embed = discord.Embed(title="🔄 能力重置", color=discord.Color.blue())
        embed.add_field(name="退回能力點", value=f"+{refund} 點", inline=True)
        embed.add_field(name="花費", value=f"🪙 安幣 -{RESET_COST}", inline=True)
        embed.add_field(name="屬性", value=f"攻/防/血 回復基礎值", inline=False)
        embed.set_footer(text="每週限一次")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(StatsAbility(bot))
