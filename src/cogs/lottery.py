import random
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user
from src.channel_guard import require_channel

TZ = timezone(timedelta(hours=8))
NUM_RANGE = 20
PICK_COUNT = 3

PRIZE_MULTIPLIERS = {"first": 100, "second": 10, "third": 5}


class Lottery(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="lottery_auto", description="托幣彩券電腦選號（01~20選3）")
    @app_commands.describe(bet="投注金額（托幣）")
    async def lottery_auto(self, interaction: discord.Interaction, bet: int):
        if not await require_channel(interaction, "lottery_auto"):
            return
        if bet < 10:
            await interaction.response.send_message("🔴 最低投注金為 10 托幣。", ephemeral=True)
            return
        nums = sorted(random.sample(range(1, NUM_RANGE + 1), PICK_COUNT))
        await self._place_bet(interaction, nums, bet)

    @app_commands.command(name="lottery_buy", description="托幣彩券手動選號（01~20選3）")
    @app_commands.describe(n1="號碼1 (1~20)", n2="號碼2", n3="號碼3", bet="投注金額（托幣）")
    async def lottery_buy(self, interaction: discord.Interaction,
                          n1: int, n2: int, n3: int, bet: int):
        if not await require_channel(interaction, "lottery_buy"):
            return
        nums = [n1, n2, n3]
        if any(n < 1 or n > NUM_RANGE for n in nums):
            await interaction.response.send_message(f"🔴 號碼需在 1~{NUM_RANGE} 之間。", ephemeral=True)
            return
        if len(set(nums)) != PICK_COUNT:
            await interaction.response.send_message("🔴 號碼不可重複。", ephemeral=True)
            return
        await self._place_bet(interaction, nums, bet)

    async def _place_bet(self, interaction, nums, bet):
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            if user["tuo_bi"] < bet:
                await interaction.response.send_message(
                    f"🔴 托幣不足！需要 {bet:,} 元，當前 {user['tuo_bi']:,} 元。"
                )
                return
            await db.execute(
                "UPDATE users SET tuo_bi=tuo_bi-$1 WHERE discord_id=$2",
                bet, str(interaction.user.id),
            )
            round_row = await db.fetchrow(
                "SELECT round_id FROM lottery_rounds WHERE status='open' ORDER BY round_id DESC LIMIT 1"
            )
            if not round_row:
                winning = sorted(random.sample(range(1, NUM_RANGE + 1), PICK_COUNT + 1))
                round_row = await db.fetchrow(
                    "INSERT INTO lottery_rounds (numbers, status) VALUES ($1, 'open') RETURNING round_id",
                    winning,
                )
            await db.execute(
                "INSERT INTO lottery_tickets (round_id, user_id, numbers, bet, is_auto) "
                "VALUES ($1,$2,$3,$4,TRUE)",
                round_row["round_id"], str(interaction.user.id), nums, bet,
            )

        await interaction.response.send_message(
            f"🎟 已投注！號碼：{' '.join(f'{n:02d}' for n in nums)} | 金額：{bet:,} 托幣", ephemeral=True
        )
        try:
            await interaction.user.send(
                f"🎟 **托幣彩券 投注確認**\n"
                f"號碼：{' '.join(f'{n:02d}' for n in nums)}\n"
                f"投注金：{bet:,} 托幣\n"
                f"開獎時間：每週六 20:05\n"
                f"祝你中獎！"
            )
        except discord.Forbidden:
            pass

    @app_commands.command(name="lottery_check", description="查看最新一期彩券結果")
    async def lottery_check(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "lottery_check"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            round_row = await db.fetchrow(
                "SELECT * FROM lottery_rounds ORDER BY round_id DESC LIMIT 1"
            )
            if not round_row:
                await interaction.response.send_message("🎟 尚無彩券期數。")
                return

            winning = round_row["numbers"]
            main_nums = winning[:PICK_COUNT]
            special = winning[PICK_COUNT] if len(winning) > PICK_COUNT else None

            tickets = await db.fetch(
                "SELECT * FROM lottery_tickets WHERE round_id=$1 AND user_id=$2",
                round_row["round_id"], str(interaction.user.id),
            )

            results = []
            for t in tickets:
                t = dict(t)
                user_nums = t["numbers"]
                bet = t.get("bet", 500)
                matches = len(set(user_nums) & set(main_nums))
                has_special = special and special in user_nums

                if matches == PICK_COUNT:
                    prize = bet * PRIZE_MULTIPLIERS["first"]
                    results.append(f"🏆 頭獎！中 {matches} 碼 → +{prize:,} 托幣")
                    await db.execute(
                        "UPDATE users SET tuo_bi=tuo_bi+$1 WHERE discord_id=$2",
                        prize, str(interaction.user.id),
                    )
                elif matches == 2 and has_special:
                    prize = bet * PRIZE_MULTIPLIERS["second"]
                    results.append(f"🥈 貳獎！中 {matches}+特別號 → +{prize:,} 托幣")
                    await db.execute(
                        "UPDATE users SET tuo_bi=tuo_bi+$1 WHERE discord_id=$2",
                        prize, str(interaction.user.id),
                    )
                elif matches >= 2:
                    prize = bet * PRIZE_MULTIPLIERS["third"]
                    results.append(f"🥉 叁獎！中 {matches} 碼 → +{prize:,} 托幣")
                    await db.execute(
                        "UPDATE users SET tuo_bi=tuo_bi+$1 WHERE discord_id=$2",
                        prize, str(interaction.user.id),
                    )
                else:
                    results.append(f"未中獎（{matches} 碼），繼續努力！")

        embed = discord.Embed(title="🎟 托幣彩券兌獎", color=discord.Color.gold())
        embed.add_field(
            name="本期獎號",
            value=f"主號碼：{' '.join(f'**{n:02d}**' for n in main_nums)}\n"
                  f"特別號：**{special:02d}**" if special else "",
            inline=False,
        )
        embed.add_field(name="你的結果", value="\n".join(results), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="lottery_rules", description="查看托幣彩券遊戲規則")
    async def lottery_rules(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="💰 托幣彩券 — 遊戲說明",
            description=(
                "從 01~20 中任選 **3 個號碼** 進行投注。\n"
                "開獎時隨機開出 **3 個號碼 + 1 個特別號**。\n"
                "選號中 2 個以上即為中獎（特別號僅適用於貳獎）。"
            ),
            color=discord.Color.gold(),
        )
        embed.add_field(name="🏆 頭獎", value=f"中 3 碼：投注金 ×{PRIZE_MULTIPLIERS['first']}", inline=True)
        embed.add_field(name="🥈 貳獎", value=f"中 2 碼 + 特別號：投注金 ×{PRIZE_MULTIPLIERS['second']}", inline=True)
        embed.add_field(name="🥉 叁獎", value=f"中 2 碼：投注金 ×{PRIZE_MULTIPLIERS['third']}", inline=True)
        embed.add_field(name="🕗 時間", value="週日開放投注 → 週六 20:00 截止 → 20:05 開獎", inline=False)
        embed.add_field(name="💡 指令", value="/lottery_auto <金額> 或 /lottery_buy <n1> <n2> <n3> <金額>", inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Lottery(bot))
