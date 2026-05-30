from datetime import date

import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user, require_alive
from src.hotconfig import game_params
from src.channel_guard import require_channel


class Daily(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="daily", description="在冒險者公會每日簽到，領取安幣獎勵")
    async def daily(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "daily"):
            return
        base_an_bi = await game_params.daily_base_an_bi or 100
        streak_bonus = await game_params.daily_streak_bonus or 20
        daily_max = await game_params.daily_max_an_bi or 250
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return

            node = await db.fetchrow("SELECT name FROM map_nodes WHERE id=$1", user.get("current_node"))
            if not node or node["name"] != "冒險者公會":
                await interaction.response.send_message(
                    "🔴 請先到 **冒險者公會** 簽到！使用 `/move 冒險者公會`。", ephemeral=True
                )
                return
        base_an_bi = await game_params.daily_base_an_bi or 100
        streak_bonus = await game_params.daily_streak_bonus or 20
        daily_max = await game_params.daily_max_an_bi or 250
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message(
                    "🔴 請先使用 `/register` 註冊！", ephemeral=True
                )
                return
            if not await require_alive(interaction, user):
                return

            today = date.today()
            last_signin = user["last_signin"]
            streak = user["signin_streak"]

            if last_signin and isinstance(last_signin, date):
                if last_signin == today:
                    await interaction.response.send_message(
                        "🔴 你今天已經簽到過了！明天再來吧。", ephemeral=True
                    )
                    return
                delta = (today - last_signin).days
                if delta == 1:
                    streak += 1
                else:
                    streak = 1
            else:
                streak = 1

            an_bi_reward = min(base_an_bi + (streak - 1) * streak_bonus, daily_max)
            yi_bi_reward = 0
            card_info = ""

            monthly_card = user["monthly_card"]
            expiry = user["monthly_expiry"]
            if monthly_card and expiry and isinstance(expiry, date) and expiry >= today:
                if monthly_card == "gold":
                    yi_bi_reward = gold_yi_bi
                    card_info = "（黃金月卡加成）"
                elif monthly_card == "diamond":
                    yi_bi_reward = diamond_yi_bi
                    card_info = "（鑽石月卡加成）"

            await db.execute(
                "UPDATE users SET an_bi=an_bi+$1, yi_bi=yi_bi+$2, signin_streak=$3, last_signin=$4 "
                "WHERE discord_id=$5",
                an_bi_reward, yi_bi_reward, streak, today, str(interaction.user.id),
            )

            referral_bonus = 0
            if streak >= 3:
                referred_by = user.get("referred_by")
                rewarded = user.get("referral_rewarded")
                if referred_by and not rewarded:
                    await db.execute(
                        "UPDATE users SET referral_rewarded=TRUE WHERE discord_id=$1",
                        str(interaction.user.id),
                    )
                    await db.execute(
                        "UPDATE users SET an_bi=an_bi+500 WHERE discord_id=$1",
                        referred_by,
                    )
                    referral_bonus = 500
                    referrer = await db.fetchrow(
                        "SELECT username FROM users WHERE discord_id=$1", referred_by
                    )
                    if referrer:
                        try:
                            member = interaction.guild.get_member(int(referred_by))
                            if member:
                                await member.send(
                                    f"🎉 **{user['username']}** 透過你的推薦碼加入了安逸烏托邦，"
                                    f"並已連續簽到 3 天！\n你獲得 🪙 安幣 +500！"
                                )
                        except:
                            pass

            await db.execute(
                "INSERT INTO signin_logs (user_id, signin_date, streak, reward_an_bi, reward_yi_bi) "
                "VALUES ($1,$2,$3,$4,$5) ON CONFLICT (user_id, signin_date) DO NOTHING",
                str(interaction.user.id), today, streak, an_bi_reward, yi_bi_reward,
            )

        embed = discord.Embed(
            title="🎉 簽到成功！",
            color=discord.Color.green(),
        )
        embed.add_field(name="本次簽到獎勵", value=f"🪙 安幣 +{an_bi_reward} 元", inline=True)
        if yi_bi_reward > 0:
            embed.add_field(name="月卡獎勵", value=f"💵 逸幣 +{yi_bi_reward} 元 {card_info}", inline=True)
        embed.add_field(name="連續簽到", value=f"🔥 {streak} 天", inline=True)
        if referral_bonus > 0:
            embed.add_field(name="🤝 推薦獎勵", value=f"+500 安幣（推薦人同步獲得）", inline=True)
        embed.set_footer(text="每天簽到累積獎勵越多！")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Daily(bot))
