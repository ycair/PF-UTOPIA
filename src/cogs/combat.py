import random
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands
from discord import app_commands

from src.database import get_pool, get_user
from src.hotconfig import combat_zones, dungeon_bosses, world_boss, game_params
from src.channel_guard import require_channel

TZ = timezone(timedelta(hours=8))


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


async def _require_outside_city(interaction: discord.Interaction, user: dict) -> bool:
    if not user.get("current_node"):
        await interaction.response.send_message(
            "🔴 你尚未出城！請先使用 `/move` 移動到城外節點。", ephemeral=True
        )
        return False
    node = await _get_node(interaction, user["current_node"])
    if not node or node["is_safe"] and node["node_type"] == "capital":
        await interaction.response.send_message(
            "🔴 城內無法戰鬥！請先使用 `/move` 出城。", ephemeral=True
        )
        return False
    return True


async def _get_node(interaction, node_id):
    pool = await get_pool()
    async with pool.acquire() as db:
        return await db.fetchrow("SELECT * FROM map_nodes WHERE id=$1", node_id)


async def _get_active_pet_bonus(db, user_id):
    pet = await db.fetchrow("""
        SELECT p.attack_bonus, p.defense_bonus, p.hp_bonus
        FROM user_pets up JOIN pets p ON p.id = up.pet_id
        WHERE up.user_id=$1 AND up.is_active=TRUE
    """, user_id)
    return {"atk": pet["attack_bonus"] if pet else 0,
            "def": pet["defense_bonus"] if pet else 0,
            "hp": pet["hp_bonus"] if pet else 0}


async def _get_node_debuff(db, user_id, stat="def"):
    user = await db.fetchrow("SELECT current_node FROM users WHERE discord_id=$1", user_id)
    if not user or not user["current_node"]:
        return 1.0
    node = await db.fetchrow("SELECT debuff FROM map_nodes WHERE id=$1", user["current_node"])
    if not node or not node["debuff"]:
        return 1.0
    debuff = node["debuff"]
    if "防禦力" in debuff and "50%" in debuff and stat == "def":
        return 0.5
    return 1.0


async def _find_path(db, start_id, end_id):
    from collections import deque
    edges = await db.fetch("SELECT from_node, to_node FROM map_edges")
    graph = {}
    for e in edges:
        graph.setdefault(e["from_node"], []).append(e["to_node"])
        graph.setdefault(e["to_node"], []).append(e["from_node"])
    if start_id not in graph or end_id not in graph:
        return None
    queue = deque([[start_id]])
    visited = {start_id}
    while queue:
        path = queue.popleft()
        node = path[-1]
        if node == end_id:
            return path
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])
    return None


def _roll_drops(drop_table):
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


def _rewards_json(rewards):
    import json
    return json.dumps(rewards, ensure_ascii=False) if rewards.get("items") else None


NODE_ZONE_MAP = {
    "初始草原": ["initial_grassland_outer"],
    "翡翠森林": ["jade_forest_outer"],
    "沿海小徑": ["coastal_path"],
    "搗蛋精靈之森": ["spirit_forest"],
    "寵物天堂": ["pet_heaven"],
}


NODE_BOSS_MAP = {
    "舊城邦": ["zombie", "army"],
    "山林後的花園": ["maid_ribbon", "maid_ribbons"],
}


async def _get_atk_buff(db, user):
    mult = user.get("atk_buff_mult") or 1.0
    expires = user.get("atk_buff_expires")
    if expires and mult > 1.0:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=TZ)
        if datetime.now(TZ) > expires:
            await db.execute(
                "UPDATE users SET atk_buff_mult=1.0, atk_buff_expires=NULL WHERE discord_id=$1",
                user["discord_id"],
            )
            return 1.0, None
        return mult, expires
    return 1.0, None


class Combat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="explore", description="探索你所在節點的野區，消耗體力與怪物戰鬥")
    async def explore(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "explore"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            if not await _require_outside_city(interaction, user):
                return

            node = await db.fetchrow("SELECT name FROM map_nodes WHERE id=$1", user["current_node"])
            if not node:
                await interaction.response.send_message("🔴 所在節點無法探索。", ephemeral=True)
                return

            zone_keys = NODE_ZONE_MAP.get(node["name"])
            if not zone_keys:
                await interaction.response.send_message(f"🔴 **{node['name']}** 無法探索戰鬥。", ephemeral=True)
                return

            zone_key = random.choice(zone_keys)
            zone_data = await combat_zones.get(zone_key)
            if not zone_data:
                await interaction.response.send_message("🔴 此區域暫無怪物資料。", ephemeral=True)
                return

            stamina_cost = zone_data["stamina"]
            if user["stamina"] < stamina_cost:
                await interaction.response.send_message(
                    f"🔴 體力不足！需要 {stamina_cost} 點，當前 {user['stamina']} 點。"
                )
                return

            u_hp = user["current_hp"] if user.get("current_hp") is not None else user["hp"]

            if u_hp <= 0:
                await interaction.response.send_message(
                    "💀 你已經陣亡了！使用 `/revive` 花費 1,500 托幣復活。", ephemeral=True
                )
                return

            atk_buff, buff_expires = await _get_atk_buff(db, user)
            await db.execute(
                "UPDATE users SET stamina=stamina-$1 WHERE discord_id=$2",
                stamina_cost, str(interaction.user.id),
            )

            enemy = random.choice(zone_data["enemies"])
            pet = await _get_active_pet_bonus(db, user["discord_id"])
            u_atk = int((user["attack"] + pet["atk"]) * atk_buff)
            u_def = int((user["defense"] + pet["def"]) * await _get_node_debuff(db, user["discord_id"]))

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

            await db.execute(
                "UPDATE users SET current_hp=$1 WHERE discord_id=$2",
                max(0, round(u_hp, 1)), str(interaction.user.id),
            )
            await db.execute(
                "INSERT INTO battle_logs (user_id, zone, enemy, result, turns, damage_dealt, damage_taken, rewards) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
                str(interaction.user.id), zone_data["name"], enemy["name"], result, turn_count,
                0, 0, _rewards_json(rewards),
            )

        dead = u_hp <= 0
        embed = discord.Embed(
            title=f"{'💀 陣亡！' if dead else '✅ 勝利！' if won else '🔴 戰鬥失敗'}",
            description=f"**{interaction.user.display_name}** 在 **{zone_data['name']}** 遭遇 **{enemy['name']}**",
            color=discord.Color.dark_grey() if dead else discord.Color.green() if won else discord.Color.red(),
        )
        embed.add_field(name=f"戰鬥記錄（{turn_count} 回合）", value=f"```{await build_battle_log(turns)}```", inline=False)
        if won:
            reward_lines = []
            for item_name, qty in rewards.get("items", {}).items():
                reward_lines.append(f"📦 {item_name} ×{qty}")
            embed.add_field(name="🎁 掉落獎勵", value="\n".join(reward_lines) if reward_lines else "沒有掉落物品", inline=False)
            if atk_buff > 1.0 and buff_expires:
                remaining = buff_expires - datetime.now(TZ)
                m = int(remaining.total_seconds() // 60)
                s = int(remaining.total_seconds() % 60)
                embed.add_field(name="⚡ 攻擊加成", value=f"+{int((atk_buff-1)*100)}% 剩餘 {m}分{s}秒", inline=True)

        footer = f"剩餘體力：{user['stamina'] - stamina_cost} 點 | HP：{max(0, round(u_hp, 1))}/{user['hp']}"
        if node and node["name"] in ("翡翠森林", "初始草原") and won and random.random() < 0.15:
            footer += f" | 🌲 迷路深入內部！再次探索可遇更強怪物"
        embed.set_footer(text=footer)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dungeon", description="挑戰你所在節點的副本 Boss")
    async def dungeon(self, interaction: discord.Interaction):
        if not await require_channel(interaction, "dungeon"):
            return
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            if not await _require_outside_city(interaction, user):
                return

            node = await db.fetchrow("SELECT name FROM map_nodes WHERE id=$1", user["current_node"])
            boss_keys = NODE_BOSS_MAP.get(node["name"], []) if node else []
            if not boss_keys:
                await interaction.response.send_message(
                    f"🔴 **{node['name']}** 沒有可挑戰的 Boss。", ephemeral=True
                )
                return
            boss = random.choice(boss_keys)
            boss_data = await dungeon_bosses.get(boss)
            if not boss_data:
                await interaction.response.send_message("🔴 Boss 資料異常。", ephemeral=True)
                return

            score = user["attack"] * 100 + user["defense"] * 50 + user["hp"] * 10
            if score < boss_data["recommended_power"] * 0.7:
                await interaction.response.send_message(
                    f"🔴 戰力不足！需要至少 {int(boss_data['recommended_power'] * 0.7):,} 分。"
                )
                return

            if user["stamina"] < boss_data["stamina"]:
                await interaction.response.send_message(f"🔴 體力不足！需要 {boss_data['stamina']} 點。")
                return

            atk_buff, buff_expires = await _get_atk_buff(db, user)
            await db.execute(
                "UPDATE users SET stamina=stamina-$1 WHERE discord_id=$2",
                boss_data["stamina"], str(interaction.user.id),
            )

            pet = await _get_active_pet_bonus(db, user["discord_id"])
            u_atk = int((user["attack"] + pet["atk"]) * atk_buff)
            u_def = int((user["defense"] + pet["def"]) * await _get_node_debuff(db, user["discord_id"]))
            dmg_mult = 1.2 if score >= boss_data["perfect_power"] else 1.0

            e_hp = boss_data["hp"]
            turns = []
            turn_count = 0
            won = False
            for _ in range(100):
                turn_count += 1
                dmg = compute_damage(u_atk, boss_data["def"]) * dmg_mult
                e_hp -= dmg
                turns.append(f"你對 Boss 造成 {dmg:.1f} 點傷害，Boss 剩下 {max(0, e_hp):.1f} 血")
                if e_hp <= 0:
                    won = True
                    break
                dmg = compute_damage(boss_data["atk"], u_def)
                u_hp -= dmg
                turns.append(f"Boss 對你造成 {dmg:.1f} 點傷害，你剩下 {max(0, u_hp):.1f} 血")
                if u_hp <= 0:
                    break

            rewards = {}
            if won:
                rewards = _roll_drops(boss_data["drops"])
                await _apply_rewards(db, user["discord_id"], rewards)

            await db.execute(
                "UPDATE users SET current_hp=$1 WHERE discord_id=$2",
                max(0, round(u_hp, 1)), str(interaction.user.id),
            )
            await db.execute(
                "INSERT INTO battle_logs (user_id, zone, enemy, result, turns, damage_dealt, damage_taken, rewards) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
                str(interaction.user.id), boss_data["name"], boss_data["name"],
                "win" if won else "lose", turn_count, 0, 0, _rewards_json(rewards),
            )

        dead = u_hp <= 0
        embed = discord.Embed(
            title=f"{'💀 陣亡！' if dead else '✅ 討伐成功！' if won else '🔴 戰鬥失敗'}",
            description=f"副本：**{boss_data['name']}**",
            color=discord.Color.dark_grey() if dead else discord.Color.gold() if won else discord.Color.red(),
        )
        embed.add_field(name=f"戰鬥記錄（{turn_count} 回合）", value=f"```{await build_battle_log(turns)}```", inline=False)
        if won:
            rl = [f"📦 {k} ×{v}" for k, v in rewards.get("items", {}).items()]
            embed.add_field(name="🎁 獎勵", value="\n".join(rl) if rl else "沒有掉落物品", inline=False)
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
            if not await _require_outside_city(interaction, user):
                return

            node = await db.fetchrow("SELECT name FROM map_nodes WHERE id=$1", user["current_node"])
            if not node or node["name"] != "世界魔皇巢穴":
                await interaction.response.send_message(
                    "🔴 必須在 **世界魔皇巢穴** 才能討伐彩虹羊！請先 `/move 世界魔皇巢穴`。", ephemeral=True
                )
                return

            today = datetime.now(TZ).date()
            attempts = await db.fetchval(
                "SELECT attempt_count FROM world_boss_attempts WHERE user_id=$1 AND attempt_date=$2",
                str(interaction.user.id), today,
            ) or 0
            if attempts >= 2:
                await interaction.response.send_message("🔴 今日圍剿次數已用完（每日 2 次）。")
                return

            boss = await db.fetchrow("SELECT * FROM world_boss_hp WHERE id=1")
            if not boss or boss["current_hp"] <= 0:
                await interaction.response.send_message("🌈 彩虹羊已被擊敗，等待管理員重置。")
                return

            atk_buff, _ = await _get_atk_buff(db, user)
            pet = await _get_active_pet_bonus(db, user["discord_id"])
            u_atk = int((user["attack"] + pet["atk"]) * atk_buff)
            u_def = int((user["defense"] + pet["def"]) * await _get_node_debuff(db, user["discord_id"]))
            original_hp = user["current_hp"] if user.get("current_hp") is not None else user["hp"]
            u_hp = user["hp"]

            boss_def = boss["def"]
            boss_hp = boss["current_hp"]
            total_dmg = 0
            turns = []
            turn_count = 0
            survived = True
            DAMAGE_CAP = 80000
            MAX_ROUNDS = 35

            for _ in range(MAX_ROUNDS):
                turn_count += 1
                dmg = compute_damage(u_atk, boss_def)
                dmg = min(dmg, DAMAGE_CAP)
                total_dmg += dmg
                boss_hp -= dmg
                boss_def = int(boss_def * 1.05)
                turns.append(f"你對彩虹羊造成 {dmg:.1f} 點傷害（防禦提升至 {boss_def}）")
                if boss_hp <= 0:
                    survived = True
                    break
                t_dmg = compute_damage(boss["atk"], u_def) * 1.2
                u_hp -= t_dmg
                turns.append(f"彩虹羊對你造成 {t_dmg:.1f} 點傷害")
                if u_hp <= 0:
                    survived = False
                    break

            killed = boss_hp <= 0
            await db.execute(
                "UPDATE world_boss_hp SET current_hp=GREATEST($1, 0), def=$2 WHERE id=1",
                boss_hp, boss_def if not killed else boss["def"],
            )
            await db.execute(
                "INSERT INTO world_boss_damage (user_id, damage) VALUES ($1,$2) "
                "ON CONFLICT (user_id) DO UPDATE SET damage=world_boss_damage.damage+$2",
                str(interaction.user.id), total_dmg,
            )
            await db.execute(
                "INSERT INTO world_boss_attempts (user_id, attempt_date, attempt_count) VALUES ($1,$2,1) "
                "ON CONFLICT (user_id, attempt_date) DO UPDATE SET attempt_count=world_boss_attempts.attempt_count+1",
                str(interaction.user.id), today,
            )
            await db.execute(
                "UPDATE users SET current_hp=$1 WHERE discord_id=$2",
                original_hp, str(interaction.user.id),
            )

            total_damage = await db.fetchval(
                "SELECT damage FROM world_boss_damage WHERE user_id=$1", str(interaction.user.id)
            ) or total_dmg

            if killed:
                await db.execute(
                    "INSERT INTO world_boss_kill (user_id) VALUES ($1)",
                    str(interaction.user.id),
                )
                await db.execute(
                    "UPDATE users SET yi_bi=yi_bi+30 WHERE discord_id=$1",
                    str(interaction.user.id),
                )

            milestones = [10000, 25000, 50000, 100000]
            rewards = {10000: 50, 25000: 50, 50000: 100, 100000: 200}
            milestones_hit = []
            for m in milestones:
                if total_damage >= m:
                    claimed = await db.fetchval(
                        "SELECT 1 FROM world_boss_milestones WHERE user_id=$1 AND milestone=$2",
                        str(interaction.user.id), m,
                    )
                    if not claimed:
                        await db.execute(
                            "INSERT INTO world_boss_milestones (user_id, milestone) VALUES ($1,$2)",
                            str(interaction.user.id), m,
                        )
                        wu = rewards[m]
                        await db.execute(
                            "UPDATE users SET wu_bi=wu_bi+$1 WHERE discord_id=$2",
                            wu, str(interaction.user.id),
                        )
                        milestones_hit.append((m, wu))

        embed = discord.Embed(
            title=f"🌈 幻彩暴走・彩虹羊 — {'💀 擊殺！' if killed else '討伐結束'}",
            color=discord.Color.purple() if killed else discord.Color.blue(),
        )
        embed.add_field(name="造成傷害", value=f"{total_dmg:,.1f} 點", inline=True)
        embed.add_field(name="回合數", value=f"{turn_count}/{MAX_ROUNDS}", inline=True)
        embed.add_field(name="剩餘 HP", value=f"{max(0, boss_hp):,.0f} / {boss['max_hp']:,}", inline=True)
        embed.add_field(
            name="⚡ 場地效果",
            value="🛡️ 七彩羊毛：每回合防禦 +5%\n🌈 虹光共振：敵方傷害 +20%\n🛑 傷害上限：80,000/回合",
            inline=False,
        )
        embed.add_field(name="戰鬥記錄", value=f"```{await build_battle_log(turns)}```", inline=False)
        if killed:
            embed.add_field(name="👑 擊殺者", value=f"**{interaction.user.display_name}** +30 逸幣！", inline=False)
        if milestones_hit:
            lines = [f"🏆 {m:,} 點 → +{w} 烏幣" for m, w in milestones_hit]
            embed.add_field(name="🎯 里程碑達成", value="\n".join(lines), inline=False)
        embed.set_footer(text=f"剩餘次數：{2 - (attempts + 1)} 次 | 累積傷害：{total_damage:,.0f} 點")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="move", description="移動到另一個地圖節點")
    @app_commands.describe(target="目標節點")
    @app_commands.choices(target=[
        app_commands.Choice(name="🏰 烏托邦主城", value="烏托邦主城"),
        app_commands.Choice(name="🌱 初始草原", value="初始草原"),
        app_commands.Choice(name="🌲 翡翠森林", value="翡翠森林"),
        app_commands.Choice(name="🌊 沿海小徑", value="沿海小徑"),
        app_commands.Choice(name="💣 競技場", value="競技場"),
        app_commands.Choice(name="⛪ 女僕教堂", value="女僕教堂"),
        app_commands.Choice(name="🎟 彩券中心", value="彩券中心"),
        app_commands.Choice(name="📊 投資交易所", value="投資交易所"),
        app_commands.Choice(name="😈 世界魔皇巢穴", value="世界魔皇巢穴"),
        app_commands.Choice(name="🍬 搗蛋精靈之森", value="搗蛋精靈之森"),
        app_commands.Choice(name="🏯 大士爺廟", value="大士爺廟"),
        app_commands.Choice(name="🥏 寵物天堂", value="寵物天堂"),
        app_commands.Choice(name="🏚️ 舊城邦", value="舊城邦"),
        app_commands.Choice(name="🌸 山林後的花園", value="山林後的花園"),
    ])
    async def move(self, interaction: discord.Interaction, target: str):
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            if user["meditating"]:
                await interaction.response.send_message("🔴 打坐中無法移動！請先 `/meditate_stop`。", ephemeral=True)
                return
            if user.get("travel_target"):
                await interaction.response.send_message("🔴 你已經在移動中！", ephemeral=True)
                return

            target_node = await db.fetchrow("SELECT id, name FROM map_nodes WHERE name=$1", target)
            if not target_node:
                await interaction.response.send_message("🔴 未知節點。", ephemeral=True)
                return

            current = user.get("current_node")
            if not current:
                await interaction.response.send_message("🔴 請先註冊後再移動。", ephemeral=True)
                return

            if current == target_node["id"]:
                await interaction.response.send_message(f"🔴 你已經在 {target} 了！", ephemeral=True)
                return

            await interaction.response.defer()

            try:
                edge = await db.fetchrow(
                    "SELECT * FROM map_edges WHERE (from_node=$1 AND to_node=$2) OR (from_node=$2 AND to_node=$1)",
                    current, target_node["id"],
                )

                if edge:
                    path_ids = [current, target_node["id"]]
                else:
                    path_ids = await _find_path(db, current, target_node["id"])
                    if not path_ids:
                        await interaction.followup.send("🔴 無法抵達此節點。", ephemeral=True)
                        return

                secs_per = await game_params.move_seconds_per_distance or 30
                next_node = path_ids[1]
                next_edge = await db.fetchrow(
                    "SELECT * FROM map_edges WHERE (from_node=$1 AND to_node=$2) OR (from_node=$2 AND to_node=$1)",
                    current, next_node,
                )
                travel_secs = next_edge["base_distance"] * secs_per
                remaining = path_ids[2:] if len(path_ids) > 2 else []

                path_names = []
                for pid in path_ids[1:]:
                    n = await db.fetchrow("SELECT name FROM map_nodes WHERE id=$1", pid)
                    path_names.append(n["name"] if n else "?")

                await db.execute(
                    "UPDATE users SET travel_target=$1, travel_path=$2, travel_start=NOW() WHERE discord_id=$3",
                    next_node, remaining, str(interaction.user.id),
                )

                route_str = " → ".join(path_names)
                cur_name = await db.fetchval("SELECT name FROM map_nodes WHERE id=$1", current)

                await interaction.followup.send(
                    f"🚶 **{cur_name}** → **{route_str}**\n"
                    f"下一步：**{path_names[0]}**（{travel_secs} 秒）"
                )
            except Exception as e:
                await interaction.followup.send(f"🔴 移動失敗：{e}", ephemeral=True)
                import traceback
                traceback.print_exc()

    @app_commands.command(name="travel_status", description="查看當前移動狀態或抵達")
    async def travel_status(self, interaction: discord.Interaction):
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            target_id = user.get("travel_target")
            if not target_id:
                cur = await db.fetchrow("SELECT name FROM map_nodes WHERE id=$1", user.get("current_node"))
                node_name = cur["name"] if cur else "未知"
                await interaction.response.send_message(f"📍 你目前在 **{node_name}**，沒有進行中的移動。")
                return

            now = datetime.now(TZ)
            start = user["travel_start"]
            if start and start.tzinfo is None:
                start = start.replace(tzinfo=TZ)

            target = await db.fetchrow("SELECT name FROM map_nodes WHERE id=$1", target_id)
            cur = await db.fetchrow("SELECT id, node_type FROM map_nodes WHERE id=$1", user["current_node"])
            target_id_int = user["current_node"]
            edge = await db.fetchrow(
                "SELECT * FROM map_edges WHERE (from_node=$1 AND to_node=$2) OR (from_node=$2 AND to_node=$1)",
                target_id_int, target_id,
            )

            if edge and start:
                travel_secs = edge["base_distance"] * (await game_params.move_seconds_per_distance or 30)
                elapsed = (now - start).total_seconds()
                if elapsed >= travel_secs:
                    await db.execute(
                        "UPDATE users SET current_node=$1, travel_target=NULL, travel_start=NULL WHERE discord_id=$2",
                        target_id, str(interaction.user.id),
                    )
                    await interaction.response.send_message(f"✅ 你已抵達 **{target['name']}**！")
                else:
                    remain = travel_secs - elapsed
                    await interaction.response.send_message(
                        f"🚶 移動中：→ **{target['name']}**\n剩餘時間：**{int(remain)} 秒**"
                    )
            else:
                await interaction.response.send_message(f"📍 你目前在 **{cur['name'] if cur else '未知'}**。")

    @app_commands.command(name="move_cancel", description="取消進行中的移動")
    async def move_cancel(self, interaction: discord.Interaction):
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            if not user.get("travel_target"):
                await interaction.response.send_message("📍 你沒有進行中的移動。", ephemeral=True)
                return
            await db.execute(
                "UPDATE users SET travel_target=NULL, travel_start=NULL, travel_path=NULL WHERE discord_id=$1",
                str(interaction.user.id),
            )
        await interaction.response.send_message("🛑 移動已取消。")

    @app_commands.command(name="revive", description="花費 1,500 托幣復活，出生於主城滿血")
    async def revive(self, interaction: discord.Interaction):
        pool = await get_pool()
        async with pool.acquire() as db:
            user = await get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("🔴 請先註冊！", ephemeral=True)
                return
            if (user.get("current_hp") if user.get("current_hp") is not None else user["hp"]) > 0:
                await interaction.response.send_message("你還活著，不需要復活。", ephemeral=True)
                return
            if user["tuo_bi"] < 1500:
                await interaction.response.send_message(
                    f"🔴 托幣不足！需要 1,500 元，當前 {user['tuo_bi']:,} 元。"
                )
                return
            main = await db.fetchval("SELECT id FROM map_nodes WHERE name='烏托邦主城'")
            await db.execute(
                "UPDATE users SET current_hp=hp, current_node=$1, tuo_bi=tuo_bi-1500 WHERE discord_id=$2",
                main, str(interaction.user.id),
            )
        await interaction.response.send_message("✨ 你已復活！出生於 **烏托邦主城**，滿血狀態。")

    @app_commands.command(name="world_boss_rank", description="查看世界魔皇全服傷害排行榜")
    async def world_boss_rank(self, interaction: discord.Interaction):
        pool = await get_pool()
        async with pool.acquire() as db:
            boss = await db.fetchrow("SELECT current_hp, max_hp FROM world_boss_hp WHERE id=1")
            rankings = await db.fetch(
                "SELECT u.username, wb.damage FROM world_boss_damage wb "
                "JOIN users u ON u.discord_id=wb.user_id ORDER BY wb.damage DESC LIMIT 10"
            )
            killer = await db.fetchrow(
                "SELECT u.username, wk.killed_at FROM world_boss_kill wk "
                "JOIN users u ON u.discord_id=wk.user_id ORDER BY wk.killed_at DESC LIMIT 1"
            )

        embed = discord.Embed(title="🌈 全服傷害沖榜 — 彩虹羊", color=discord.Color.purple())
        if boss:
            pct = max(0, boss["current_hp"] / boss["max_hp"] * 100)
            embed.add_field(name="剩餘血量", value=f"{boss['current_hp']:,} / {boss['max_hp']:,}（{pct:.1f}%）", inline=False)
        if killer:
            embed.add_field(name="👑 上次擊殺者", value=f"**{killer['username']}**", inline=False)

        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        lines = []
        for i, r in enumerate(rankings, 1):
            medal = medals.get(i, f"{i}.")
            lines.append(f"{medal} **{r['username']}** — {r['damage']:,.0f} 傷害")
        embed.add_field(name="傷害排行榜", value="\n".join(lines) if lines else "尚無記錄", inline=False)
        embed.add_field(name="🏆 獎勵", value="🥇 400 烏幣 | 🥈🥉 200 烏幣", inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Combat(bot))
