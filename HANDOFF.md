# PF UTOPIA — 安逸烏托邦 Discord MMORPG

You are continuing development on PF UTOPIA, a Discord-based MMORPG text game with 55+ slash commands, 15 nodes on a graph map, persistent HP, 5-currency economy, stock trading, lottery, pet system, world boss, faith system, and an interactive web dashboard.

## Tech Stack
- **Language**: Python 3.13
- **Discord**: discord.py 2.7
- **Database**: PostgreSQL 16 + asyncpg (localhost:5432, database: utopia)
- **Web**: aiohttp static server on localhost:8080
- **Tunnel**: Cloudflare Tunnel → utopia.ycair.space
- **Config**: Hot-reload JSON (`settings.json`)

## Project Structure
```
YCAIR-DCBOT/
├── bot1_main.py          # Bot ① — RPG core, combat, faith, social, utility, reaction_roles, guild
├── bot2_main.py          # Bot ② — shop, lottery, investment, pet, achievements, ranking, events
├── web_server.py          # Web server (OAuth, API endpoints, static files)
├── settings.json          # Hot-reload config (channels, game params, combat zones)
├── src/
│   ├── config.py          # Tokens, GUILD_ID, DB_URL
│   ├── database.py        # PostgreSQL schema, seed data, price updates
│   ├── hotconfig.py       # Hot-reload config manager
│   ├── channel_guard.py   # Channel restriction system
│   ├── referral.py        # Hashids referral encoding
│   ├── bmc_webhook.py     # Buy Me a Coffee webhook
│   ├── gm/                # AI GM interface stubs (NOT active)
│   │   ├── context.py, llm.py, tools.py
│   └── cogs/
│       ├── registration.py, profile.py, daily.py, inventory.py
│       ├── combat.py (explore, dungeon, world_boss, move, revive)
│       ├── faith.py (meditate_start/stop, pray)
│       ├── stats_ability.py (ability, ability_reset)
│       ├── social.py, utility.py, reaction_roles.py, guild.py
│       ├── shop.py, lottery.py, investment.py
│       ├── pet.py, achievements.py, ranking.py, events.py
├── web/                   # Frontend (v0.dev designed)
│   ├── index.html, style.css, map.js
│   ├── callback.html, install.html, referral.html
│   ├── tos.html, privacy.html
│   ├── map_config.json (15 node pixel coordinates)
│   └── assets/ (map.png 2528×1696, elements.png)
├── note/
│   ├── architecture.md    # Full technical specification (1130+ lines)
│   └── feature-update.md  # AI GM / map / dashboard expansion plan
└── README.md              # Player-facing game documentation
```

## How to Start

```bash
# 1. Ensure PostgreSQL is running
pg_isready -h localhost || /usr/local/opt/postgresql@16/bin/postgres -D /usr/local/var/postgresql@16 &

# 2. Start Bot ① (RPG core)
cd /Volumes/YCAIR/YCAIR-DCBOT
.venv/bin/python bot1_main.py

# 3. Start Bot ② (economy) — separate terminal
.venv/bin/python bot2_main.py

# 4. Start Web server — separate terminal
DISCORD_CLIENT_SECRET="..." .venv/bin/python web_server.py

# 5. Start Cloudflare Tunnel — separate terminal
cloudflared tunnel --no-autoupdate run ycair-share-tunnel
```

## Key Architecture Decisions

### Currency Flow
```
簽到 → 安幣 → 能力重置
BMC → 逸幣 → 體力恢復
活動 → 烏幣 → 戰力/體力上限
賣戰利品 → 托幣 → 買道具/彩券/股票
全服 → 邦幣 → 世界建設(規劃中)
```

### Map (15 nodes, graph-based)
- **City nodes** (safe, 3s travel): 主城, 競技場, 彩券中心, 投資交易所, 女僕教堂, 冒險者公會
- **Wild nodes**: 初始草原(唯一閘道), 翡翠森林, 沿海小徑, 搗蛋精靈之森, 寵物天堂
- **Dungeon nodes**: 世界魔皇巢穴, 舊城邦(☢️輻射-50%防禦), 山林後的花園
- **Temple**: 大士爺廟(鬼王庇佑, 每日領香膜拜)
- `/move` auto-navigates via BFS; `/move_cancel` to stop

### HP System
- Persistent HP across battles (`current_hp` column)
- NOT `0 or hp` — use `is not None` check (fixed falsy bug)
- Heal: 回主城自動滿血, 大士爺廟膜拜滿血, 恢復劑
- Death: `/revive` 1500托幣, 出生主城

### Faith System
- **女僕教堂**: `/meditate_start` → offline grind → `/meditate_stop` (must be at node)
- **大士爺廟**: `/pray` (daily incense from DM popup, reads from backpack)

### World Boss
- 幻彩暴走・彩虹羊 HP 5,500,000 (shared), must be at 世界魔皇巢穴
- 2 attempts/day, no stamina cost
- Mechanics: defense growth +5%/round, dmg cap 80K, 35-round limit
- Manual reset only

### Adventurer Rank
- 35 levels: 瓷 I~V → 鐵 I~V → 銀 I~V → 金 I~V → 白金 I~V → 秘銀 I~V → 精金 I~V
- Formula: `(level+1)*50*(1+ln(level+1)*0.8)`
- `/rank_certify` at 冒險者公會 to level up; EXP source not yet implemented

### Stock System
- 6 turtle stocks, daily 8:00/12:00/16:00 price updates
- Bankruptcy at ≤19; 紅寶石 -20%~+30%, others -10%~+10%

### Shop System
- City: full items 100% price; Wild: local drops only, max 30% city price
- Consumables: city=base, wild=+20%
- Price model: mean-reverting (`pull + noise`), NOT multiplicative

## Recent Changes (Last Session)

1. ✅ 冒險者公會 node + /daily migration + /quests + /rank_certify
2. ✅ /use supports quantity parameter
3. ✅ /pray reads incense from backpack (not daily_incense counter)
4. ✅ /move_cancel to stop travel
5. ✅ City edges travel time = 3 seconds
6. ✅ World boss requires 世界魔皇巢穴 node
7. ✅ Incense popup duplicate fixed (now checks daily_incense before showing DM)
8. ✅ node_prices synced with shop_sell_prices on update; mean-reverting price model
9. ✅ Reaction roles system (7 message groups)
10. ✅ Referral system (Hashids, 2500安幣, sharing page)

## Known Quirks

- `/move` uses `defer()` to avoid timeout on BFS pathfinding
- Web login requires `DISCORD_CLIENT_SECRET` env var
- `settings.json` is hot-reloadable (no restart needed for config changes)
- Bot ① handles all background tasks (stamina, travel, prices)
- IncenseView buttons need `defer()` to avoid 3s timeout

## If You Need Context

- Read `note/architecture.md` for full technical specs
- Read `README.md` for player-facing documentation
- All game parameters in `settings.json` (combat zones, bosses, prices)
- All channel IDs in `settings.json` → `channels` and `channel_map`
