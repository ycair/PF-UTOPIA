import random
import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user
from src.channel_guard import require_channel

ANSWER_BOOK_REPLIES = [
    "毫無疑問。", "很明顯是的。", "當然是這樣。", "是的，絕對是。",
    "你可以相信。", "如我所見，是的。", "很有可能。", "前景看好。",
    "是的。", "跡象指向是的。", "回覆模糊，再試一次。", "稍後再問。",
    "現在不適合告訴你。", "現在無法預測。", "集中精神再問一次。",
    "不要指望它。", "我的回覆是不。", "我的來源說不。", "前景不太好。",
    "非常可疑。", "絕對不是。", "不可能。", "想太多了。",
]


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="draw_lots", description="從選項中隨機抽取")
    @app_commands.describe(count="抽幾籤", options="選項（用逗號分隔，例如：蘋果,香蕉,橘子）")
    async def draw_lots(self, interaction: discord.Interaction, count: int, options: str):
        if not await require_channel(interaction, "draw_lots"):
            return
        opts = [o.strip() for o in options.split(",") if o.strip()]
        if len(opts) < 2:
            await interaction.response.send_message("🔴 至少需要兩個選項。", ephemeral=True)
            return
        if count < 1 or count > len(opts):
            await interaction.response.send_message(f"🔴 抽籤數量需在 1~{len(opts)} 之間。", ephemeral=True)
            return
        results = random.sample(opts, count)
        await interaction.response.send_message(
            f"🎰 從 {len(opts)} 個選項中抽出 {count} 籤：\n"
            + "\n".join(f"{i+1}. **{r}**" for i, r in enumerate(results))
        )

    @app_commands.command(name="dice", description="猜大小")
    @app_commands.describe(guess="猜大還是小")
    @app_commands.choices(guess=[
        app_commands.Choice(name="大", value="big"),
        app_commands.Choice(name="小", value="small"),
    ])
    async def dice(self, interaction: discord.Interaction, guess: str):
        if not await require_channel(interaction, "dice"):
            return
        roll = random.randint(1, 6)
        result = "big" if roll >= 4 else "small"
        won = guess == result
        await interaction.response.send_message(
            f"🎲 擲出了 **{roll}** 點 → {'大' if result == 'big' else '小'}！"
            f" {'你猜對了！✅' if won else '你猜錯了...❌'}"
        )

    @app_commands.command(name="guess_number", description="猜數字 (1~100)")
    @app_commands.describe(number="你猜的數字")
    async def guess_number(self, interaction: discord.Interaction, number: int):
        if not await require_channel(interaction, "guess_number"):
            return
        if number < 1 or number > 100:
            await interaction.response.send_message("🔴 請輸入 1~100 之間的數字。", ephemeral=True)
            return
        answer = random.randint(1, 100)
        if number == answer:
            msg = f"🎯 答案是 **{answer}**！你猜對了！"
        elif number < answer:
            msg = f"🎯 答案是 **{answer}**，你猜的 **{number}** 太小了！"
        else:
            msg = f"🎯 答案是 **{answer}**，你猜的 **{number}** 太大了！"
        await interaction.response.send_message(msg)

    @app_commands.command(name="slot", description="拉霸機")
    async def slot(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "slot"):
            return
        symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
        result = [random.choice(symbols) for _ in range(3)]
        if len(set(result)) == 1:
            outcome = "🎉 JACKPOT！三個一樣！"
        elif len(set(result)) == 2:
            outcome = "不錯！兩個一樣！"
        else:
            outcome = "再接再厲！"
        await interaction.response.send_message(
            f"🎰 **拉霸機**\n`[ {' | '.join(result)} ]`\n{outcome}"
        )

    @app_commands.command(name="rps", description="剪刀石頭布")
    @app_commands.describe(choice="你的選擇")
    @app_commands.choices(choice=[
        app_commands.Choice(name="✂️ 剪刀", value="scissors"),
        app_commands.Choice(name="🪨 石頭", value="rock"),
        app_commands.Choice(name="📄 布", value="paper"),
    ])
    async def rps(self, interaction: discord.Interaction, choice: str):
        bot_choice = random.choice(["scissors", "rock", "paper"])
        emoji_map = {"scissors": "✂️", "rock": "🪨", "paper": "📄"}
        name_map = {"scissors": "剪刀", "rock": "石頭", "paper": "布"}

        if choice == bot_choice:
            result = "平手！"
        elif (choice == "scissors" and bot_choice == "paper") or \
             (choice == "rock" and bot_choice == "scissors") or \
             (choice == "paper" and bot_choice == "rock"):
            result = "你贏了！🎉"
        else:
            result = "你輸了！😢"

        await interaction.response.send_message(
            f"你出了 {emoji_map[choice]} **{name_map[choice]}**\n"
            f"女僕出了 {emoji_map[bot_choice]} **{name_map[bot_choice]}**\n"
            f"→ {result}"
        )

    @app_commands.command(name="answer_book", description="解答之書 — 問一個是非題")
    @app_commands.describe(question="你的問題")
    async def answer_book(self, interaction: discord.Interaction, question: str):
        if not await require_channel(interaction, "answer_book"):
            return
        answer = random.choice(ANSWER_BOOK_REPLIES)
        embed = discord.Embed(
            title="📖 解答之書",
            color=discord.Color.dark_purple(),
        )
        embed.add_field(name="你的問題", value=question, inline=False)
        embed.add_field(name="解答", value=f"**{answer}**", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="yesno", description="是非問答 — 機器人幫你決定")
    @app_commands.describe(question="你的問題")
    async def yesno(self, interaction: discord.Interaction, question: str):
        if not await require_channel(interaction, "yesno"):
            return
        answer = random.choice(["✅ 是！", "❌ 不是！", "🤔 或許吧...", "💫 命運如此安排！"])
        await interaction.response.send_message(f"**問：{question}**\n**答：{answer}**")

    @app_commands.command(name="avatar", description="取得用戶頭像")
    @app_commands.describe(user="目標用戶（留空則取得自己的）")
    async def avatar(self, interaction: discord.Interaction, user: discord.Member | None = None):
        target = user or interaction.user
        embed = discord.Embed(title=f"{target.display_name} 的頭像", color=discord.Color.blurple())
        embed.set_image(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ping", description="查詢機器人延遲")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🏓 延遲：**{latency}ms**")

    @app_commands.command(name="iwin", description="直接勝利！")
    async def iwin(self, interaction: discord.Interaction):
        await interaction.response.send_message("🏆 **直接勝利！** 沒有人可以阻止你！")

    @app_commands.command(name="divider", description="產生一條分隔線")
    async def divider(self, interaction: discord.Interaction):
        await interaction.response.send_message("=" * 40)

    @app_commands.command(name="nickname", description="更改你在伺服器中的暱稱")
    @app_commands.describe(name="新暱稱")
    async def nickname(self, interaction: discord.Interaction, name: str):
        try:
            await interaction.user.edit(nick=name)
            await interaction.response.send_message(f"✅ 暱稱已更改為 **{name}**", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("🔴 我沒有權限更改你的暱稱。", ephemeral=True)

    @app_commands.command(name="anon", description="匿名留言（僅管理員可查看發送者）")
    @app_commands.describe(message="要發送的匿名訊息")
    async def anon(self, interaction: discord.Interaction, message: str):
        if not await require_channel(interaction, "anon"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            await db.execute(
                "INSERT INTO anon_messages (user_id, content) VALUES ($1,$2)",
                str(interaction.user.id), message,
            )
        await interaction.response.send_message("✅ 匿名留言已發送。", ephemeral=True)

    @app_commands.command(name="clean", description="批量刪除訊息（限管理員）")
    @app_commands.describe(count="要刪除的訊息數量 (1~100)")
    @app_commands.default_permissions(manage_messages=True)
    async def clean(self, interaction: discord.Interaction, count: int):
        if not await require_channel(interaction, "clean"):
            return
        count = min(max(count, 1), 100)
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=count)
        await interaction.followup.send(f"✅ 已刪除 {len(deleted)} 則訊息。", ephemeral=True)

    @app_commands.command(name="dm_me", description="讓機器人私訊你")
    async def dm_me(self, interaction: discord.Interaction):
        try:
            await interaction.user.send("👋 你好！這是安逸烏托邦女僕的私訊～")
            await interaction.response.send_message("✅ 已私訊你！", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(
                "🔴 無法私訊你，請確認你的隱私設定允許伺服器成員私訊。", ephemeral=True
            )

    @app_commands.command(name="vote_create", description="發起投票")
    @app_commands.describe(title="投票主題", option_a="選項 A", option_b="選項 B",
                           option_c="選項 C（可選）", option_d="選項 D（可選）")
    async def vote_create(self, interaction: discord.Interaction, title: str,
                          option_a: str, option_b: str,
                          option_c: str | None = None, option_d: str | None = None):
        if not await require_channel(interaction, "vote_create"):
            return
        options = [option_a, option_b]
        if option_c:
            options.append(option_c)
        if option_d:
            options.append(option_d)

        emojis = ["🇦", "🇧", "🇨", "🇩"]
        lines = [f"{emojis[i]} {opt}" for i, opt in enumerate(options)]
        embed = discord.Embed(
            title=f"📊 {title}",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        embed.set_footer(text=f"由 {interaction.user.display_name} 發起")
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        for i in range(len(options)):
            try:
                await msg.add_reaction(emojis[i])
            except discord.HTTPException:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
