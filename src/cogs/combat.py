import random
import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user
from src.hotconfig import combat_zones, dungeon_bosses, world_boss, game_params
from src.channel_guard import require_channel


def compute_damage(attacker_atk, defender_def, variance=0.2):
    base = max(1, attacker_atk - defender_def * 0.5)
    return round(base * random.uniform(1 - variance, 1 + variance), 1)


async def _max_battle_rounds():
    return await game_params.max_battle_log_rounds or 5


async def build_battle_log(turns):
    max_show = await _max_battle_rounds()
    if len(turns) <= max_show:
        return "\n".join(turns)
    recent = turns[-max_show:]
    return f"...（省略前 {len(turns) - max_show} 條記錄）\n" + "\n".join(recent)


class Combat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="explore", description="探索野區，消耗體力與怪物戰鬥")
    @app_commands.describe(zone="選擇探索區域")
    @app_commands.choices(zone=[
        app_commands.Choice(name="初始草原外圍 (8體)", value="initial_grassland_outer"),
        app_commands.Choice(name="初始草原內部 (10體)", value="initial_grassland_inner"),
        app_commands.Choice(name="翡翠森林外圍 (12體)", value="jade_forest_outer"),
        app_commands.Choice(name="翡翠森林內部 (15體)", value="jade_forest_inner"),
        app_commands.Choice(name="沿海小徑 (14體)", value="coastal_path"),
    ])
    async def explore(self, interaction: discord.Interaction, zone: str):
        if not await require_channel(interaction, "explore"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return

            zone_data = await combat_zones.get(zone)
            if not zone_data:
                await interaction.response.send_message("🔴 未知區域。", ephemeral=True)
                return

            if user["stamina"] < zone_data["stamina"]:
                await interaction.response.send_message(
                    f"🔴 體力不夠！需要 {zone_data['stamina']} 點，當前 {user['stamina']} 點。\n"
                    f"使用 `/use 體力恢復劑` 恢復體力。"
                )
                return

            await db.execute(
                "UPDATE users SET stamina=stamina-$1 WHERE discord_id=$2",
                zone_data["stamina"], str(interaction.user.id),
            )

            enemy = random.choice(zone_data["enemies"])
            pet_bonus = await _get_active_pet_bonus(db, user["discord_id"])

            u_atk = user["attack"] + pet_bonus["atk"]
            u_def = user["defense"] + pet_bonus["def"]
            u_hp_total = user["hp"] + pet_bonus["hp"]
            u_hp = u_hp_total

            e_hp = enemy["hp"]
            e_atk = enemy["atk"]
            e_def = enemy["def"]

            turns = []
            turn_count = 0
            won = False
            for _ in range(50):
                turn_count += 1
                dmg = compute_damage(u_atk, e_def)
                e_hp -= dmg
                turns.append(f"你對 {enemy['name']} 造成 {dmg} 點傷害，{enemy['name']} 剩下 {max(0, e_hp):.1f} 血")
                if e_hp <= 0:
                    won = True
                    break
                dmg = compute_damage(e_atk, u_def)
                u_hp -= dmg
                turns.append(f"{enemy['name']} 對你造成 {dmg} 點傷害，你剩下 {max(0, u_hp):.1f} 血")
                if u_hp <= 0:
                    break

            result = "win" if won else "lose"
            rewards = {}
            if won:
                rewards = _roll_drops(enemy["drops"])
                await _apply_rewards(db, user["discord_id"], rewards)
                exp_gain = random.uniform(1, 3)
                await db.execute(
                    "UPDATE users SET chat_exp=chat_exp+$1 WHERE discord_id=$2",
                    exp_gain, str(interaction.user.id),
                )

            await db.execute(
                "INSERT INTO battle_logs (user_id, zone, enemy, result, turns, damage_dealt, damage_taken, rewards) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
                str(interaction.user.id), zone_data["name"], enemy["name"], result, turn_count,
                u_atk * turn_count / 2, e_atk * turn_count / 2, _rewards_json(rewards),
            )

        embed = discord.Embed(
            title=f"{'✅ 勝利！' if won else '🔴 戰鬥失敗'}",
            description=f"**{interaction.user.display_name}** 在 **{zone_data['name']}** 遭遇 **{enemy['name']}**",
            color=discord.Color.green() if won else discord.Color.red(),
        )
        embed.add_field(
            name=f"戰鬥記錄（{turn_count} 回合）",
            value=f"```{await build_battle_log(turns)}```",
            inline=False,
        )
        if won:
            reward_lines = []
            for item_name, qty in rewards.get("items", {}).items():
                reward_lines.append(f"📦 {item_name} ×{qty}")
            for curr, amt in rewards.get("currencies", {}).items():
                reward_lines.append(f"💰 {curr} +{amt}")
            embed.add_field(
                name="🎁 掉落獎勵",
                value="\n".join(reward_lines) if reward_lines else "沒有掉落物品",
                inline=False,
            )
        embed.set_footer(text=f"剩餘體力：{user['stamina'] - zone_data['stamina']} 點")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dungeon", description="挑戰副本 Boss")
    @app_commands.describe(boss="選擇 Boss")
    @app_commands.choices(boss=[
        app_commands.Choice(name="征服入侵殭屍 (建議戰力 2,800)", value="zombie"),
        app_commands.Choice(name="征服入侵軍團 (建議戰力 24,300)", value="army"),
        app_commands.Choice(name="解開女僕的緞帶 (建議戰力 218,700)", value="maid_ribbon"),
        app_commands.Choice(name="解開女僕們的緞帶 (建議戰力 1,749,600)", value="maid_ribbons"),
    ])
    async def dungeon(self, interaction: discord.Interaction, boss: str):
        if not await require_channel(interaction, "dungeon"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return

            boss_data = await dungeon_bosses.get(boss)
            if not boss_data:
                await interaction.response.send_message("🔴 未知 Boss。", ephemeral=True)
                return

            score = user["attack"] * 100 + user["defense"] * 50 + user["hp"] * 10
            if score < boss_data["recommended_power"] * 0.7:
                await interaction.response.send_message(
                    f"🔴 你的戰力不足！需要至少 {int(boss_data['recommended_power'] * 0.7):,} 分，當前 {score:,} 分。"
                )
                return

            if user["stamina"] < boss_data["stamina"]:
                await interaction.response.send_message(f"🔴 體力不足！需要 {boss_data['stamina']} 點。")
                return

            await db.execute(
                "UPDATE users SET stamina=stamina-$1 WHERE discord_id=$2",
                boss_data["stamina"], str(interaction.user.id),
            )

            pet_bonus = await _get_active_pet_bonus(db, user["discord_id"])
            u_atk = user["attack"] + pet_bonus["atk"]
            u_def = user["defense"] + pet_bonus["def"]
            u_hp_total = user["hp"] + pet_bonus["hp"]
            u_hp = u_hp_total
            dmg_mult = 1.2 if score >= boss_data["perfect_power"] else 1.0

            e_hp = boss_data["hp"]
            e_atk = boss_data["atk"]
            e_def = boss_data["def"]

            turns = []
            turn_count = 0
            won = False
            for _ in range(100):
                turn_count += 1
                dmg = compute_damage(u_atk, e_def) * dmg_mult
                e_hp -= dmg
                turns.append(f"你對 Boss 造成 {dmg:.1f} 點傷害，Boss 剩下 {max(0, e_hp):.1f} 血")
                if e_hp <= 0:
                    won = True
                    break
                dmg = compute_damage(e_atk, u_def)
                u_hp -= dmg
                turns.append(f"Boss 對你造成 {dmg:.1f} 點傷害，你剩下 {max(0, u_hp):.1f} 血")
                if u_hp <= 0:
                    break

            result = "win" if won else "lose"
            rewards = {}
            if won:
                rewards = _roll_drops(boss_data["drops"])
                await _apply_rewards(db, user["discord_id"], rewards)

            await db.execute(
                "INSERT INTO battle_logs (user_id, zone, enemy, result, turns, damage_dealt, damage_taken, rewards) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
                str(interaction.user.id), boss_data["name"], boss_data["name"], result, turn_count,
                u_atk * turn_count / 2, e_atk * turn_count / 2, _rewards_json(rewards),
            )

        embed = discord.Embed(
            title=f"{'✅ 討伐成功！' if won else '🔴 戰鬥失敗，建議提升戰力。'}",
            description=f"副本：**{boss_data['name']}**",
            color=discord.Color.gold() if won else discord.Color.red(),
        )
        embed.add_field(name=f"戰鬥記錄（{turn_count} 回合）", value=f"```{await build_battle_log(turns)}```", inline=False)
        if won:
            reward_text = "\n".join(
                [f"📦 {k} ×{v}" for k, v in rewards.get("items", {}).items()]
                + [f"💰 {k} +{v}" for k, v in rewards.get("currencies", {}).items()]
            )
            embed.add_field(
                name="🎁 獎勵",
                value=reward_text if reward_text else "沒有掉落物品",
                inline=False,
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="world_boss", description="挑戰世界魔皇彩虹羊")
    async def world_boss(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "world_boss"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            wb = await world_boss.all()
            if user["stamina"] < wb["stamina"]:
                await interaction.response.send_message(f"🔴 體力不足！需要 {wb['stamina']} 點。")
                return

            await db.execute(
                "UPDATE users SET stamina=stamina-$1 WHERE discord_id=$2",
                wb["stamina"], str(interaction.user.id),
            )

            pet_bonus = await _get_active_pet_bonus(db, user["discord_id"])
            u_atk = user["attack"] + pet_bonus["atk"]
            u_def = user["defense"] + pet_bonus["def"]
            u_hp_total = user["hp"] + pet_bonus["hp"]
            u_hp = u_hp_total

            e_atk = wb["atk"]
            e_def = wb["def"]

            turns = []
            turn_count = 0
            total_dmg = 0
            survived = True
            for _ in range(100):
                turn_count += 1
                dmg = compute_damage(u_atk, e_def)
                total_dmg += dmg
                turns.append(f"彩虹羊對你造成 {compute_damage(e_atk, u_def):.1f} 點傷害")
                turns.append(f"你對彩虹羊造成 {dmg:.1f} 點傷害")
                dmg_taken = compute_damage(e_atk, u_def)
                u_hp -= dmg_taken
                if u_hp <= 0:
                    survived = False
                    break

            if survived:
                an_bi_reward = int(total_dmg * 0.5)
                await db.execute(
                    "UPDATE users SET an_bi=an_bi+$1 WHERE discord_id=$2",
                    an_bi_reward, str(interaction.user.id),
                )

            await db.execute(
                "INSERT INTO battle_logs (user_id, zone, enemy, result, turns, damage_dealt, damage_taken, rewards) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
                str(interaction.user.id), "世界魔皇", "彩虹羊",
                "survived" if survived else "defeated",
                turn_count, total_dmg, e_atk * turn_count,
                _rewards_json({"currencies": {"安幣": int(total_dmg * 0.5)}} if survived else {}),
            )

        embed = discord.Embed(
            title=f"🌈 世界魔皇 — 彩虹羊",
            description=f"**{interaction.user.display_name}** {'成功存活！' if survived else '被擊敗了...'}",
            color=discord.Color.purple() if survived else discord.Color.dark_grey(),
        )
        embed.add_field(name="造成傷害", value=f"{total_dmg:,.1f} 點", inline=True)
        embed.add_field(name="存活回合", value=f"{turn_count} 回合", inline=True)
        if survived:
            embed.add_field(name="獎勵", value=f"🪙 安幣 +{an_bi_reward:,} 元", inline=True)
        embed.add_field(name="戰鬥記錄", value=f"```{await build_battle_log(turns)}```", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="altar", description="挑戰主線祭壇")
    @app_commands.describe(chapter="選擇章節 (1~15)")
    async def altar(self, interaction: discord.Interaction, chapter: int):
        if not await require_channel(interaction, "altar"):
            return
        if chapter < 1 or chapter > 15:
            await interaction.response.send_message("🔴 章節範圍為 1~15。", ephemeral=True)
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return

            stamina_cost = 8 + chapter * 2
            if user["stamina"] < stamina_cost:
                await interaction.response.send_message(f"🔴 體力不足！需要 {stamina_cost} 點。")
                return

            await db.execute(
                "UPDATE users SET stamina=stamina-$1 WHERE discord_id=$2",
                stamina_cost, str(interaction.user.id),
            )

            enemy_hp = 30 + chapter * 25
            enemy_atk = 3 + chapter * 5
            enemy_def = 1 + chapter * 2
            enemy_name = f"第{chapter}章守護者"

            pet_bonus = await _get_active_pet_bonus(db, user["discord_id"])
            u_atk = user["attack"] + pet_bonus["atk"]
            u_def = user["defense"] + pet_bonus["def"]
            u_hp_total = user["hp"] + pet_bonus["hp"]
            u_hp = u_hp_total

            turns = []
            turn_count = 0
            won = False
            for _ in range(50):
                turn_count += 1
                dmg = compute_damage(u_atk, enemy_def)
                enemy_hp -= dmg
                turns.append(f"你對 {enemy_name} 造成 {dmg:.1f} 點傷害")
                if enemy_hp <= 0:
                    won = True
                    break
                dmg = compute_damage(enemy_atk, u_def)
                u_hp -= dmg
                turns.append(f"{enemy_name} 對你造成 {dmg:.1f} 點傷害")
                if u_hp <= 0:
                    break

            rewards = {}
            if won:
                an_bi = 50 + chapter * 30
                wu_bi = chapter * 5
                await db.execute(
                    "UPDATE users SET an_bi=an_bi+$1, wu_bi=wu_bi+$2 WHERE discord_id=$3",
                    an_bi, wu_bi, str(interaction.user.id),
                )
                rewards = {"currencies": {"安幣": an_bi, "烏幣": wu_bi}}

            await db.execute(
                "INSERT INTO battle_logs (user_id, zone, enemy, result, turns, damage_dealt, damage_taken, rewards) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
                str(interaction.user.id), f"主線祭壇第{chapter}章", enemy_name,
                "win" if won else "lose", turn_count, 0, 0, _rewards_json(rewards),
            )

        embed = discord.Embed(
            title=f"🔮 主線祭壇第 {chapter} 章 — {'✅ 通關' if won else '🔴 失敗'}",
            color=discord.Color.blue() if won else discord.Color.red(),
        )
        embed.add_field(name=f"戰鬥記錄（{turn_count} 回合）", value=f"```{await build_battle_log(turns)}```", inline=False)
        if won:
            lines = [f"💰 {k} +{v}" for k, v in rewards.get("currencies", {}).items()]
            embed.add_field(name="🎁 獎勵", value="\n".join(lines) if lines else "無獎勵", inline=False)
        await interaction.response.send_message(embed=embed)


async def _get_active_pet_bonus(db, user_id) -> dict:
    pet = await db.fetchrow("""
        SELECT p.attack_bonus, p.defense_bonus, p.hp_bonus
        FROM user_pets up JOIN pets p ON p.id = up.pet_id
        WHERE up.user_id=$1 AND up.is_active=TRUE
    """, user_id)
    if pet:
        return {"atk": pet["attack_bonus"], "def": pet["defense_bonus"], "hp": pet["hp_bonus"]}
    return {"atk": 0, "def": 0, "hp": 0}


def _roll_drops(drop_table) -> dict:
    items = {}
    for item_name, qty_min, qty_max, chance in drop_table:
        if random.random() < chance:
            items[item_name] = random.randint(qty_min, qty_max)
    return {"items": items, "currencies": {}}


async def _apply_rewards(db, user_id, rewards):
    for item_name, qty in rewards.get("items", {}).items():
        item = await db.fetchrow("SELECT id FROM items WHERE name=$1", item_name)
        if item:
            await db.execute(
                "INSERT INTO inventory (user_id, item_id, quantity) VALUES ($1,$2,$3) "
                "ON CONFLICT (user_id, item_id) DO UPDATE SET quantity=inventory.quantity+$3",
                user_id, item["id"], qty,
            )
    for curr, amt in rewards.get("currencies", {}).items():
        col_map = {"安幣": "an_bi", "逸幣": "yi_bi", "烏幣": "wu_bi", "托幣": "tuo_bi", "邦幣": "bang_bi"}
        col = col_map.get(curr)
        if col:
            await db.execute(f"UPDATE users SET {col}={col}+$1 WHERE discord_id=$2", amt, user_id)


def _rewards_json(rewards) -> str | None:
    import json
    return json.dumps(rewards, ensure_ascii=False) if (rewards.get("items") or rewards.get("currencies")) else None


async def setup(bot: commands.Bot):
    await bot.add_cog(Combat(bot))
