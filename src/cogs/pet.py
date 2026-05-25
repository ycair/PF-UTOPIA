import random
import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user
from src.channel_guard import require_channel

PET_GACHA_COST = 500
PET_GACHA_PITY = 50

PET_RATES = [
    ("教主", "legendary", 0.01),
    ("灰啾啾", "rare", 0.038),
    ("胖柴", "rare", 0.038),
    ("灰吱吱", "rare", 0.038),
    ("啾太郎", "uncommon", 0.038),
]


class Pet(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="pet_gacha", description="寵物抽卡（500逸幣/抽）")
    @app_commands.describe(count="抽卡次數（預設1）")
    async def pet_gacha(self, interaction: discord.Interaction, count: int = 1):
        if not await require_channel(interaction, "pet_gacha"):
            return
        count = min(max(count, 1), 10)
        total_cost = PET_GACHA_COST * count
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            if user["yi_bi"] < total_cost:
                await interaction.response.send_message(
                    f"🔴 逸幣不足！需要 {total_cost:,} 元，當前 {user['yi_bi']:,} 元。"
                )
                return

            await db.execute(
                "UPDATE users SET yi_bi=yi_bi-$1 WHERE discord_id=$2",
                total_cost, str(interaction.user.id),
            )

            results = []
            for _ in range(count):
                roll = random.random()
                cumulative = 0
                pet_name = None
                pet_rarity = None
                for name, rarity, rate in PET_RATES:
                    cumulative += rate
                    if roll < cumulative:
                        pet_name = name
                        pet_rarity = rarity
                        break
                results.append((pet_name, pet_rarity))

            obtained = []
            for pet_name, pet_rarity in results:
                if pet_name:
                    pet_row = await db.fetchrow("SELECT id FROM pets WHERE name=$1", pet_name)
                    if pet_row:
                        existing = await db.fetchrow(
                            "SELECT * FROM user_pets WHERE user_id=$1 AND pet_id=$2",
                            str(interaction.user.id), pet_row["id"],
                        )
                        if existing:
                            await db.execute(
                                "UPDATE user_pets SET exp=exp+10 WHERE user_id=$1 AND pet_id=$2",
                                str(interaction.user.id), pet_row["id"],
                            )
                            obtained.append(f"{pet_name}（重複 → +10 EXP）")
                        else:
                            await db.execute(
                                "INSERT INTO user_pets (user_id, pet_id, is_active) VALUES ($1,$2, FALSE)",
                                str(interaction.user.id), pet_row["id"],
                            )
                            obtained.append(f"🆕 {pet_name}（{pet_rarity}）")
                else:
                    obtained.append("💨 未中獎...")

        embed = discord.Embed(
            title="🔆 寵物抽卡",
            description=f"**{interaction.user.display_name}** 抽了 {count} 次！",
            color=discord.Color.purple(),
        )
        embed.add_field(name="結果", value="\n".join(obtained), inline=False)
        embed.set_footer(text=f"花費 {total_cost:,} 逸幣 | /pet_list 查看寵物")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pet_list", description="查看你的寵物")
    async def pet_list(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "pet_list"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            pets = await db.fetch("""
                SELECT p.*, up.level, up.exp, up.is_active
                FROM user_pets up JOIN pets p ON p.id = up.pet_id
                WHERE up.user_id=$1 ORDER BY up.is_active DESC, up.obtained_at DESC
            """, str(interaction.user.id))

        if not pets:
            await interaction.response.send_message("🔆 你還沒有任何寵物！使用 `/pet_gacha` 抽卡。")
            return

        embed = discord.Embed(
            title=f"🔆 {interaction.user.display_name} 的寵物",
            color=discord.Color.purple(),
        )
        for p in pets:
            p = dict(p)
            active_tag = " ⭐出戰中" if p["is_active"] else ""
            embed.add_field(
                name=f"{p['emoji']} {p['name']}{active_tag}",
                value=f"稀有度：{p['rarity']}\n等級：{p['level']} (EXP: {p['exp']})\n"
                      f"加成：ATK+{p['attack_bonus']} DEF+{p['defense_bonus']} HP+{p['hp_bonus']}",
                inline=True,
            )

        embed.set_footer(text="/pet_equip 出戰 | /pet_battle 寵物天堂")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pet_equip", description="選擇出戰寵物")
    @app_commands.describe(pet_name="寵物名稱")
    @app_commands.choices(pet_name=[
        app_commands.Choice(name="教主", value="教主"),
        app_commands.Choice(name="灰啾啾", value="灰啾啾"),
        app_commands.Choice(name="胖柴", value="胖柴"),
        app_commands.Choice(name="灰吱吱", value="灰吱吱"),
        app_commands.Choice(name="啾太郎", value="啾太郎"),
    ])
    async def pet_equip(self, interaction: discord.Interaction, pet_name: str):
        if not await require_channel(interaction, "pet_equip"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            pet = await db.fetchrow(
                "SELECT up.* FROM user_pets up JOIN pets p ON p.id = up.pet_id "
                "WHERE up.user_id=$1 AND p.name=$2",
                str(interaction.user.id), pet_name,
            )
            if not pet:
                await interaction.response.send_message(f"🔴 你還沒有 {pet_name}！", ephemeral=True)
                return

            await db.execute(
                "UPDATE user_pets SET is_active=FALSE WHERE user_id=$1",
                str(interaction.user.id),
            )
            await db.execute(
                "UPDATE user_pets SET is_active=TRUE WHERE user_id=$1 AND pet_id=$2",
                str(interaction.user.id), pet["pet_id"],
            )

        await interaction.response.send_message(f"✅ **{pet_name}** 已設為出戰寵物！加成將在戰鬥中生效。")

    @app_commands.command(name="pet_battle", description="寵物天堂 — 寵物專屬戰鬥（消耗5體力）")
    async def pet_battle(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "pet_battle"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            if user["stamina"] < 5:
                await interaction.response.send_message("🔴 體力不足！需要 5 點。")
                return

            active_pet = await db.fetchrow("""
                SELECT up.*, p.name, p.emoji, p.attack_bonus
                FROM user_pets up JOIN pets p ON p.id = up.pet_id
                WHERE up.user_id=$1 AND up.is_active=TRUE
            """, str(interaction.user.id))
            if not active_pet:
                await interaction.response.send_message("🔴 你沒有出戰寵物！使用 `/pet_equip` 選擇。")
                return

            await db.execute(
                "UPDATE users SET stamina=stamina-5 WHERE discord_id=$1",
                str(interaction.user.id),
            )

            exp_gain = random.randint(10, 30)
            await db.execute(
                "UPDATE user_pets SET exp=exp+$1 WHERE user_id=$2 AND pet_id=$3",
                exp_gain, str(interaction.user.id), active_pet["pet_id"],
            )

            pet = await db.fetchrow(
                "SELECT * FROM user_pets WHERE user_id=$1 AND pet_id=$2",
                str(interaction.user.id), active_pet["pet_id"],
            )

            level_up = ""
            exp_needed = pet["level"] * 50
            if pet["exp"] >= exp_needed:
                await db.execute(
                    "UPDATE user_pets SET level=level+1, exp=exp-$1 WHERE user_id=$2 AND pet_id=$3",
                    exp_needed, str(interaction.user.id), active_pet["pet_id"],
                )
                level_up = f"\n🎉 **{active_pet['name']}** 升到 Lv.{pet['level'] + 1}！"

        await interaction.response.send_message(
            f"🥏 **寵物天堂**\n{active_pet['emoji']} **{active_pet['name']}** (Lv.{pet['level']}) 完成了訓練！\n"
            f"EXP +{exp_gain}{level_up}"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Pet(bot))
