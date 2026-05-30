import json
import random
import math
from datetime import datetime, timezone, date

import asyncpg
from asyncpg.pool import Pool

DB_URL = "postgresql://localhost:5432/utopia"

_pool: Pool | None = None


async def get_pool() -> Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DB_URL, min_size=2, max_size=10)
    return _pool


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            discord_id      TEXT PRIMARY KEY,
            username        TEXT NOT NULL,
            registered_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            stamina         INTEGER NOT NULL DEFAULT 150,
            max_stamina     INTEGER NOT NULL DEFAULT 150,
            yuan_shen       INTEGER NOT NULL DEFAULT 0,
            xiu_wei         INTEGER NOT NULL DEFAULT 0,
            xian_xiang      INTEGER NOT NULL DEFAULT 0,
            chat_level      INTEGER NOT NULL DEFAULT 0,
            chat_exp        DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            chat_exp_next   DOUBLE PRECISION NOT NULL DEFAULT 50.0,
            attack          INTEGER NOT NULL DEFAULT 10,
            defense         INTEGER NOT NULL DEFAULT 5,
            hp              INTEGER NOT NULL DEFAULT 100,
            ability_points  INTEGER NOT NULL DEFAULT 0,
            an_bi           INTEGER NOT NULL DEFAULT 0,
            yi_bi           INTEGER NOT NULL DEFAULT 0,
            wu_bi           INTEGER NOT NULL DEFAULT 0,
            tuo_bi          INTEGER NOT NULL DEFAULT 0,
            bang_bi         INTEGER NOT NULL DEFAULT 0,
            monthly_card    TEXT,
            monthly_expiry  DATE,
            signin_streak   INTEGER NOT NULL DEFAULT 0,
            last_signin     DATE,
            candy           INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS items (
            id              SERIAL PRIMARY KEY,
            name            TEXT NOT NULL UNIQUE,
            description     TEXT NOT NULL DEFAULT '',
            item_type       TEXT NOT NULL DEFAULT 'material',
            rarity          TEXT NOT NULL DEFAULT 'common',
            base_price      INTEGER NOT NULL DEFAULT 0,
            buy_price       INTEGER NOT NULL DEFAULT 0,
            emoji           TEXT NOT NULL DEFAULT '📦'
        );

        CREATE TABLE IF NOT EXISTS inventory (
            user_id         TEXT NOT NULL REFERENCES users(discord_id) ON DELETE CASCADE,
            item_id         INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
            quantity        INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (user_id, item_id)
        );

        CREATE TABLE IF NOT EXISTS shop_sell_prices (
            item_id         INTEGER PRIMARY KEY REFERENCES items(id) ON DELETE CASCADE,
            current_price   INTEGER NOT NULL,
            direction       TEXT NOT NULL DEFAULT 'flat',
            last_update      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS lottery_rounds (
            round_id        SERIAL PRIMARY KEY,
            numbers         INTEGER[] NOT NULL,
            drawn_at        TIMESTAMPTZ,
            status          TEXT NOT NULL DEFAULT 'open'
        );

        CREATE TABLE IF NOT EXISTS lottery_tickets (
            id              SERIAL PRIMARY KEY,
            round_id        INTEGER NOT NULL REFERENCES lottery_rounds(round_id) ON DELETE CASCADE,
            user_id         TEXT NOT NULL REFERENCES users(discord_id) ON DELETE CASCADE,
            numbers         INTEGER[] NOT NULL,
            is_vip          BOOLEAN NOT NULL DEFAULT FALSE,
            is_auto         BOOLEAN NOT NULL DEFAULT FALSE,
            purchased_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS stocks (
            id              SERIAL PRIMARY KEY,
            code            TEXT NOT NULL UNIQUE,
            name            TEXT NOT NULL,
            current_price   INTEGER NOT NULL,
            emoji           TEXT NOT NULL DEFAULT '🐢',
            volatility      DOUBLE PRECISION NOT NULL DEFAULT 0.05
        );

        CREATE TABLE IF NOT EXISTS user_stocks (
            user_id         TEXT NOT NULL REFERENCES users(discord_id) ON DELETE CASCADE,
            stock_id        INTEGER NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
            quantity        INTEGER NOT NULL DEFAULT 0,
            avg_cost        INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, stock_id)
        );

        CREATE TABLE IF NOT EXISTS stock_history (
            id              SERIAL PRIMARY KEY,
            stock_id        INTEGER NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
            price           INTEGER NOT NULL,
            recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS battle_logs (
            id              SERIAL PRIMARY KEY,
            user_id         TEXT NOT NULL REFERENCES users(discord_id) ON DELETE CASCADE,
            zone            TEXT NOT NULL,
            enemy           TEXT NOT NULL,
            result          TEXT NOT NULL,
            turns           INTEGER NOT NULL,
            damage_dealt    DOUBLE PRECISION NOT NULL DEFAULT 0,
            damage_taken    DOUBLE PRECISION NOT NULL DEFAULT 0,
            rewards         JSONB,
            battled_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS achievements (
            id              SERIAL PRIMARY KEY,
            name            TEXT NOT NULL UNIQUE,
            description     TEXT NOT NULL,
            category        TEXT NOT NULL DEFAULT 'general',
            required_value  INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS user_achievements (
            user_id         TEXT NOT NULL REFERENCES users(discord_id) ON DELETE CASCADE,
            achievement_id  INTEGER NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
            achieved_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (user_id, achievement_id)
        );

        CREATE TABLE IF NOT EXISTS arena_records (
            user_id         TEXT PRIMARY KEY REFERENCES users(discord_id) ON DELETE CASCADE,
            wins            INTEGER NOT NULL DEFAULT 0,
            losses          INTEGER NOT NULL DEFAULT 0,
            rank_points     INTEGER NOT NULL DEFAULT 1000
        );

        CREATE TABLE IF NOT EXISTS pets (
            id              SERIAL PRIMARY KEY,
            name            TEXT NOT NULL UNIQUE,
            rarity          TEXT NOT NULL,
            attack_bonus    INTEGER NOT NULL DEFAULT 0,
            defense_bonus   INTEGER NOT NULL DEFAULT 0,
            hp_bonus        INTEGER NOT NULL DEFAULT 0,
            emoji           TEXT NOT NULL DEFAULT '🐾'
        );

        CREATE TABLE IF NOT EXISTS user_pets (
            user_id         TEXT NOT NULL REFERENCES users(discord_id) ON DELETE CASCADE,
            pet_id          INTEGER NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
            level           INTEGER NOT NULL DEFAULT 1,
            exp             INTEGER NOT NULL DEFAULT 0,
            is_active       BOOLEAN NOT NULL DEFAULT FALSE,
            obtained_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (user_id, pet_id)
        );

        CREATE TABLE IF NOT EXISTS signin_logs (
            user_id         TEXT NOT NULL REFERENCES users(discord_id) ON DELETE CASCADE,
            signin_date     DATE NOT NULL,
            streak          INTEGER NOT NULL,
            reward_an_bi    INTEGER NOT NULL,
            reward_yi_bi    INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, signin_date)
        );

        CREATE TABLE IF NOT EXISTS anon_messages (
            id              SERIAL PRIMARY KEY,
            user_id         TEXT NOT NULL REFERENCES users(discord_id) ON DELETE CASCADE,
            content         TEXT NOT NULL,
            sent_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        ALTER TABLE map_nodes ADD COLUMN IF NOT EXISTS has_train_station BOOLEAN DEFAULT FALSE;
        """)


async def seed_data():
    pool = await get_pool()
    async with pool.acquire() as db:
        items = [
            # ── 現有材料 ──
            ("黏液", "軟Q的史萊姆黏液", "material", "common", 5, 100, "🫧"),
            ("羽毛", "輕飄飄的羽毛", "material", "common", 7, 100, "🪶"),
            ("肉", "新鮮的肉塊", "material", "common", 12, 100, "🥩"),
            ("羊毛", "柔軟的羊毛", "material", "common", 13, 100, "🧶"),
            ("骨頭", "堅硬的骨頭", "material", "common", 10, 100, "🦴"),
            ("牙齒", "鋒利的牙齒", "material", "uncommon", 11, 100, "🦷"),
            ("皮革", "耐用的皮革", "material", "uncommon", 16, 100, "🪵"),
            ("緞帶", "女僕的緞帶", "material", "rare", 50000, 100, "🎀"),
            ("毒液", "致命的毒液", "material", "rare", 48, 100, "🧪"),
            ("魔石", "蘊含魔力的石頭", "material", "epic", 180, 100, "💎"),
            # ── 新增材料 16 種 ──
            ("石頭", "堅硬的岩石碎片", "material", "common", 8, 100, "🪨"),
            ("木材", "神木林地的木材", "material", "common", 8, 100, "🪵"),
            ("純水", "極寒冰窟的純淨之水", "material", "common", 10, 100, "💧"),
            ("草藥", "野生的藥用植物", "material", "common", 15, 100, "🌿"),
            ("絨毛", "柔軟的動物絨毛", "material", "common", 6, 100, "☁️"),
            ("鐵礦", "可冶煉的鐵礦石", "material", "uncommon", 20, 100, "⛏️"),
            ("銅礦", "可冶煉的銅礦石", "material", "uncommon", 25, 100, "🔶"),
            ("祕銀礦", "散發微光的祕銀礦石", "material", "rare", 120, 100, "🔮"),
            ("精金礦", "極其堅硬的精金礦石", "material", "epic", 500, 100, "💠"),
            ("火焰精華", "熔岩裂谷的火焰結晶", "material", "rare", 200, 100, "🔥"),
            ("冰霜精華", "極寒冰窟的冰霜結晶", "material", "rare", 200, 100, "❄️"),
            ("紅寶石", "璀璨的紅色寶石", "material", "epic", 500, 100, "💎"),
            ("藍寶石", "清澈的藍色寶石", "material", "rare", 200, 100, "💙"),
            ("幸運草", "帶來好運的四葉草", "material", "rare", 80, 100, "🍀"),
            ("龍鱗", "遠古龍族的鱗片", "material", "legendary", 2000, 100, "🐉"),
            # ── 消耗品 ──
            ("恢復劑", "恢復50點體力與血量", "consumable", "common", 100, 100, "🧃"),
            ("強效恢復劑", "恢復150點體力與血量", "consumable", "uncommon", 300, 300, "🧋"),
            ("線香", "膜拜教堂使用", "consumable", "common", 50, 50, "🕯️"),
            ("糖果", "供奉搗蛋精靈使用", "consumable", "common", 30, 30, "🍬"),
            ("轉法輪", "修行道具", "consumable", "rare", 500, 500, "☸️"),
            ("車票", "搭乘驛站前往任意車站", "consumable", "common", 350, 350, "🎫"),
        ]
        for name, desc, itype, rarity, base_price, buy_price, emoji in items:
            await db.execute(
                "INSERT INTO items (name, description, item_type, rarity, base_price, buy_price, emoji) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7) ON CONFLICT (name) DO NOTHING",
                name, desc, itype, rarity, base_price, buy_price, emoji,
            )
        rows = await db.fetch("SELECT id, base_price, item_type FROM items")
        for row in rows:
            if row["item_type"] == "material":
                await db.execute(
                    "INSERT INTO shop_sell_prices (item_id, current_price) VALUES ($1,$2) ON CONFLICT (item_id) DO NOTHING",
                    row["id"], row["base_price"],
                )

        achievements = [
            ("初來乍到", "完成註冊", "general", 1),
            ("簽到新手", "累積簽到7天", "daily", 7),
            ("簽到達人", "累積簽到30天", "daily", 30),
            ("簽到狂人", "累積簽到100天", "daily", 100),
            ("初次戰鬥", "完成第一次戰鬥", "combat", 1),
            ("百戰勇士", "戰鬥勝利100次", "combat", 100),
            ("富豪之路", "持有安幣超過10萬元", "economy", 100000),
            ("百萬富翁", "持有安幣超過100萬元", "economy", 1000000),
            ("投資新手", "完成第一次股票買賣", "investment", 1),
            ("寵物大師", "抽到傳說級寵物", "pet", 1),
            ("彩券幸運兒", "彩券中獎", "lottery", 1),
        ]
        for name, desc, cat, val in achievements:
            await db.execute(
                "INSERT INTO achievements (name, description, category, required_value) "
                "VALUES ($1,$2,$3,$4) ON CONFLICT (name) DO NOTHING",
                name, desc, cat, val,
            )

        stocks = [
            ("bronze_turtle", "青銅烏龜", 1000, "🐢", 0.10, 0.10),
            ("silver_turtle", "白銀烏龜", 10000, "🐢", 0.10, 0.10),
            ("gold_turtle", "黃金烏龜", 100000, "🐢", 0.10, 0.10),
            ("diamond_turtle", "鑽石烏龜", 500000, "💎", 0.10, 0.10),
            ("stone_turtle", "石頭烏龜", 800, "🪨", 0.10, 0.10),
            ("ruby_turtle", "紅寶石烏龜", 1200000, "💠", 0.20, 0.30),
        ]
        for code, name, price, emoji, vol_d, vol_u in stocks:
            sid = await db.fetchval(
                "INSERT INTO stocks (code, name, current_price, emoji, vol_down, vol_up) "
                "VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT (code) DO UPDATE SET name=$2, current_price=$3, vol_down=$5, vol_up=$6 "
                "RETURNING id",
                code, name, price, emoji, vol_d, vol_u,
            )
            await db.execute(
                "INSERT INTO stock_history (stock_id, price) VALUES ($1,$2) ON CONFLICT DO NOTHING",
                sid, price,
            )

        pets = [
            ("教主", "legendary", 15, 8, 30, "👑"),
            ("灰啾啾", "rare", 8, 3, 10, "🐦"),
            ("胖柴", "rare", 4, 7, 12, "🐕"),
            ("灰吱吱", "rare", 6, 4, 8, "🐭"),
            ("啾太郎", "uncommon", 5, 5, 5, "🐤"),
        ]
        for name, rarity, atk, df, hp, emoji in pets:
            await db.execute(
                "INSERT INTO pets (name, rarity, attack_bonus, defense_bonus, hp_bonus, emoji) "
                "VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT (name) DO NOTHING",
                name, rarity, atk, df, hp, emoji,
            )

        new_nodes = [
            ("廢棄礦坑", "wild", False, "礦石資源豐富的廢棄礦坑，礦脈伴生怪群聚"),
            ("熔岩裂谷", "wild", False, "火山地質的深層裂谷，火焰元素與寶石守護者棲息"),
            ("極寒冰窟", "wild", False, "永凍的極寒洞穴，冰霜元素與雪原生態"),
            ("神木林地", "wild", False, "古老神木的林地，植物型怪物與草藥天堂"),
            ("龍眠山脈", "wild", False, "遠古龍族棲息的山脈，終局野外區域"),
        ]
        for name, ntype, is_safe, desc in new_nodes:
            await db.execute(
                "INSERT INTO map_nodes (name, node_type, is_safe, description) "
                "VALUES ($1,$2,$3,$4) ON CONFLICT (name) DO NOTHING",
                name, ntype, is_safe, desc,
            )

        new_edges = [
            ("初始草原", "廢棄礦坑", 3, 15),
            ("初始草原", "神木林地", 2, 10),
            ("翡翠森林", "熔岩裂谷", 6, 40),
            ("熔岩裂谷", "龍眠山脈", 7, 60),
            ("沿海小徑", "極寒冰窟", 4, 25),
        ]
        for f, t, dist, danger in new_edges:
            fn = await db.fetchval("SELECT id FROM map_nodes WHERE name=$1", f)
            tn = await db.fetchval("SELECT id FROM map_nodes WHERE name=$1", t)
            if fn and tn:
                await db.execute(
                    "INSERT INTO map_edges (from_node, to_node, base_distance, base_danger) "
                    "VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING",
                    fn, tn, dist, danger,
                )

        train_stations = ["烏托邦主城", "大士爺廟", "世界魔皇巢穴", "廢棄礦坑", "極寒冰窟", "龍眠山脈"]
        for name in train_stations:
            await db.execute(
                "UPDATE map_nodes SET has_train_station=TRUE WHERE name=$1", name,
            )


async def get_user(db, discord_id):
    return await db.fetchrow("SELECT * FROM users WHERE discord_id=$1", str(discord_id))


async def create_user(db, discord_id, username):
    await db.execute(
        "INSERT INTO users (discord_id, username) VALUES ($1,$2) "
        "ON CONFLICT (discord_id) DO NOTHING",
        str(discord_id), username,
    )
    return await get_user(db, discord_id)


async def get_inventory(db, user_id):
    return await db.fetch("""
        SELECT i.*, inv.quantity,
               COALESCE(np.current_price, i.base_price) AS sell_price,
               COALESCE(np.direction, 'flat') AS direction
        FROM inventory inv
        JOIN items i ON i.id = inv.item_id
        LEFT JOIN node_prices np ON np.item_id = i.id AND np.node_id=1
        WHERE inv.user_id=$1
        ORDER BY i.item_type, i.name
    """, str(user_id))


def compute_ability_score(atk, df, hp):
    return atk * 100 + df * 50 + hp * 10


def format_exp_bar(current, next_level):
    pct = current / max(next_level, 1) * 100
    filled = int(pct / 5)
    return "█" * filled + "░" * (20 - filled), pct


def user_embed_fields(user):
    score = compute_ability_score(user["attack"], user["defense"], user["hp"])
    pct = user["stamina"] / max(user["max_stamina"], 1) * 100
    exp_bar, exp_pct = format_exp_bar(user["chat_exp"], user["chat_exp_next"])
    yuan_level = user.get("yuan_shen_level") or 0
    yuan_exp = user.get("yuan_shen_exp") or 0
    yuan_next = (yuan_level + 1) * 50
    xiu_level = user.get("xiu_wei_level") or 0
    xiu_prog = user.get("xiu_wei_progress") or 0
    xiu_next = int((xiu_level + 1) * 3 * (1 + math.log(xiu_level + 1 + 1e-9) * 0.5))
    adv_rank = user.get("adventurer_rank") or 0
    adv_exp = user.get("adventurer_exp") or 0
    adv_next = int((adv_rank + 1) * 50 * (1 + math.log(adv_rank + 1 + 1e-9) * 0.8))
    from src.cogs.guild import rank_name
    rank_str = rank_name(adv_rank)
    return [
        ("狀態",
         f"能力評分：**{score}** 分\n"
         f"體力：`[{user['stamina']}pt]` {pct:.1f}%\n"
         f"最大體力：{user['max_stamina']} 點\n"
         f"元神 Lv.{yuan_level}：{yuan_exp}/{yuan_next} EXP\n"
         f"修為 Lv.{xiu_level}：{xiu_prog}/{xiu_next} 次膜拜\n"
         f"冒險者：{rank_str} ({adv_exp}/{adv_next} EXP)"),
        ("活躍",
         f"聊天等級：**{user['chat_level']}**\n"
         f"聊天經驗值：`[{user['chat_exp']:.1f}pt/{user['chat_exp_next']:.1f}pt]` {exp_pct:.1f}%"),
        ("戰力",
         f"⚔️ **攻擊**：{user['attack']}\n"
         f"🛡️ **防禦**：{user['defense']}\n"
         f"❤️ **血量**：{user['hp']}\n"
         f"🧬 **能力點**：{user['ability_points']}"),
        ("貨幣",
         f"🪙 **安幣**：{user['an_bi']:,} 元\n"
         f"💵 **逸幣**：{user['yi_bi']:,} 元\n"
         f"💶 **烏幣**：{user['wu_bi']:,} 元\n"
         f"💴 **托幣**：{user['tuo_bi']:,} 元\n"
         f"💷 **邦幣**：{user['bang_bi']:,} 元"),
    ]


async def update_stock_prices(db):
    stocks = await db.fetch("SELECT * FROM stocks WHERE bankrupt=FALSE")
    for stock in stocks:
        vol_down = float(stock.get("vol_down") or 0.1)
        vol_up = float(stock.get("vol_up") or 0.1)
        change = random.uniform(-vol_down, vol_up)
        new_price = int(stock["current_price"] * (1 + change))
        new_price = max(new_price, 1)
        if new_price <= 19:
            await db.execute("UPDATE stocks SET current_price=0, bankrupt=TRUE WHERE id=$1", stock["id"])
        else:
            await db.execute("UPDATE stocks SET current_price=$1 WHERE id=$2", new_price, stock["id"])
        await db.execute(
            "INSERT INTO stock_history (stock_id, price) VALUES ($1,$2)", stock["id"], new_price,
        )


async def update_sell_prices(db):
    prices = await db.fetch("""
        SELECT sp.*, i.base_price FROM shop_sell_prices sp JOIN items i ON i.id = sp.item_id
    """)
    for p in prices:
        base = p["base_price"]
        current = p["current_price"]
        pull = (base - current) * 0.15
        noise = base * random.uniform(-0.10, 0.10)
        new_price = int(current + pull + noise)
        new_price = max(new_price, int(base * 0.3))
        new_price = min(new_price, int(base * 3))
        direction = "up" if new_price > current else ("down" if new_price < current else "flat")
        await db.execute(
            "UPDATE shop_sell_prices SET current_price=$1, direction=$2, last_update=NOW() WHERE item_id=$3",
            new_price, direction, p["item_id"],
        )
        await db.execute(
            "UPDATE node_prices SET current_price=$1, direction=$2 WHERE node_id=1 AND item_id=$3",
            new_price, direction, p["item_id"],
        )
