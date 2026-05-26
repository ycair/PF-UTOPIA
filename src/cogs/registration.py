import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user, create_user, user_embed_fields
from src.channel_guard import require_channel
from src.referral import decode_referral, encode_referral

MAIN_CITY = "烏托邦主城"


class Registration(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="register", description="註冊成為安逸烏托邦的居民")
    @app_commands.describe(code="推薦碼（可選）")
    async def register(self, interaction: discord.Interaction, code: str | None = None):
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

            referrer_id = None
            extra_desc = ""
            if code:
                referrer_id = decode_referral(code)
                if referrer_id:
                    referrer = await get_user(db, referrer_id)
                    if referrer and str(referrer_id) != str(interaction.user.id):
                        extra_desc = f"\n🤝 透過 **{referrer['username']}** 的推薦加入！"
                    else:
                        referrer_id = None

            user = await create_user(db, interaction.user.id, interaction.user.display_name)
            if referrer_id:
                await db.execute(
                    "UPDATE users SET referred_by=$1, an_bi=an_bi+2500 WHERE discord_id=$2",
                    str(referrer_id), str(interaction.user.id),
                )

            main = await db.fetchrow("SELECT id FROM map_nodes WHERE name=$1", MAIN_CITY)
            if main:
                await db.execute(
                    "UPDATE users SET current_node=$1 WHERE discord_id=$2",
                    main["id"], str(interaction.user.id),
                )

        embed = discord.Embed(
            title="🎉 註冊成功！歡迎來到安逸烏托邦",
            description=f"<@{interaction.user.id}> 已成為安逸烏托邦的正式居民！{extra_desc}\n"
                        f"你的冒險即將開始...",
            color=discord.Color.gold(),
        )
        for name, value in user_embed_fields(user):
            embed.add_field(name=name, value=value, inline=True)
        embed.set_footer(text="使用 /daily 開始每日簽到！連續簽到 3 天有驚喜。")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="referral", description="取得你的專屬推薦碼，邀請朋友加入")
    async def referral(self, interaction: discord.Interaction):
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
        code = encode_referral(interaction.user.id)
        url = f"https://utopia.ycair.space/referral.html?code={code}"
        await interaction.response.send_message(
            f"🤝 你的專屬推薦碼：**`{code}`**\n"
            f"🔗 分享連結：{url}\n\n"
            f"新玩家使用 `/register code:{code}` 註冊可獲得 **🪙 2,500 安幣**！\n"
            f"朋友連續簽到 3 天後，你也會獲得 500 安幣獎勵。"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Registration(bot))
