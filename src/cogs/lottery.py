import random
import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user
from src.channel_guard import require_channel

LOTTERY_COST = 500
LOTTERY_VIP_COST = 1000


class Lottery(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="lottery_buy", description="手動選號購買彩券（500安幣/張）")
    @app_commands.describe(
        n1="號碼1 (1~49)", n2="號碼2", n3="號碼3", n4="號碼4", n5="號碼5", n6="號碼6"
    )
    async def lottery_buy(self, interaction: discord.Interaction,
                          n1: int, n2: int, n3: int, n4: int, n5: int, n6: int):
        if not await require_channel(interaction, "lottery_buy"):
            return
        nums = [n1, n2, n3, n4, n5, n6]
        if any(n < 1 or n > 49 for n in nums):
            await interaction.response.send_message("🔴 號碼需在 1~49 之間。", ephemeral=True)
            return
        if len(set(nums)) != 6:
            await interaction.response.send_message("🔴 號碼不可重複。", ephemeral=True)
            return
        await self._buy_ticket(interaction, nums, is_vip=False, is_auto=False)

    @app_commands.command(name="lottery_auto", description="自動隨機選號（500安幣/張）")
    async def lottery_auto(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "lottery_auto"):
            return
        nums = sorted(random.sample(range(1, 50), 6))
        await self._buy_ticket(interaction, nums, is_vip=False, is_auto=True)

    @app_commands.command(name="lottery_vip", description="VIP加成彩券（1,000安幣/張，獎金×2）")
    async def lottery_vip(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "lottery_vip"):
            return
        nums = sorted(random.sample(range(1, 50), 6))
        await self._buy_ticket(interaction, nums, is_vip=True, is_auto=True)

    async def _buy_ticket(self, interaction, nums, is_vip, is_auto):
        cost = LOTTERY_VIP_COST if is_vip else LOTTERY_COST
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            if user["an_bi"] < cost:
                await interaction.response.send_message(
                    f"🔴 安幣不足！需要 {cost:,} 元，當前 {user['an_bi']:,} 元。"
                )
                return

            await db.execute(
                "UPDATE users SET an_bi=an_bi-$1 WHERE discord_id=$2",
                cost, str(interaction.user.id),
            )

            round_row = await db.fetchrow(
                "SELECT round_id FROM lottery_rounds WHERE status='open' ORDER BY round_id DESC LIMIT 1"
            )
            if not round_row:
                winning = sorted(random.sample(range(1, 50), 6))
                round_row = await db.fetchrow(
                    "INSERT INTO lottery_rounds (numbers, status) VALUES ($1, 'open') RETURNING round_id",
                    winning,
                )

            await db.execute(
                "INSERT INTO lottery_tickets (round_id, user_id, numbers, is_vip, is_auto) "
                "VALUES ($1,$2,$3,$4,$5)",
                round_row["round_id"], str(interaction.user.id), nums, is_vip, is_auto,
            )

        tag = "VIP" if is_vip else ""
        msg = f"🎟 {'自動' if is_auto else '手動'}選號{tag}彩券\n號碼：{' '.join(f'{n:02d}' for n in nums)}\n花費：{cost:,} 安幣"
        await interaction.response.send_message(msg)

    @app_commands.command(name="lottery_check", description="查看本期彩券開獎結果")
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

            tickets = await db.fetch(
                "SELECT * FROM lottery_tickets WHERE round_id=$1 AND user_id=$2",
                round_row["round_id"], str(interaction.user.id),
            )

            winning = round_row["numbers"]
            lines = []
            for t in tickets:
                user_nums = t["numbers"]
                matches = len(set(user_nums) & set(winning))
                tag = "VIP " if t["is_vip"] else ""
                if matches == 6:
                    prize = 1_000_000 * (2 if t["is_vip"] else 1)
                    lines.append(f"🏆 {tag}頭獎！中 {matches} 碼 → +{prize:,} 安幣")
                    await db.execute(
                        "UPDATE users SET an_bi=an_bi+$1 WHERE discord_id=$2",
                        prize, str(interaction.user.id),
                    )
                elif matches >= 4:
                    prize = [0, 0, 0, 0, 1000, 10000, 50000][matches] * (2 if t["is_vip"] else 1)
                    lines.append(f"🎉 {tag}中 {matches} 碼 → +{prize:,} 安幣")
                    await db.execute(
                        "UPDATE users SET an_bi=an_bi+$1 WHERE discord_id=$2",
                        prize, str(interaction.user.id),
                    )
                else:
                    lines.append(f"未中獎（{matches} 碼），繼續努力！")

        embed = discord.Embed(title="🎟 彩券兌獎", color=discord.Color.gold())
        embed.add_field(name="本期號碼", value=" ".join(f"**{n:02d}**" for n in winning), inline=False)
        if lines:
            embed.add_field(name="你的結果", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="你的結果", value="你沒有購買本期彩券。", inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Lottery(bot))
