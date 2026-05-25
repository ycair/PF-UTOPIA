# PF UTOPIA — Feature Update: AI 時代的三核心擴展

> 分析日期：2026-05-25
> 狀態：規劃階段，尚未實作

---

## 總覽

在現有的「文字指令 → SQL CRUD → embed 回應」架構上，疊加三層新系統：

```
                      ┌─────────────────────┐
                      │   AI Game Master     │  ← 第三層：敘事 + 決策
                      │  (LLM + Tool Call)   │
                      └──────┬──────────────┘
                             │ 讀寫
        ┌────────────────────┼────────────────────┐
        │                    ▼                    │
        │  ┌─────────────────────────────────┐    │
        │  │        PostgreSQL                │    │
        │  │  + map_nodes / map_edges         │    │
        │  │  + quests / node_inventory       │    │
        │  │  + reputation / world_state      │    │
        │  └──────────────┬──────────────────┘    │
        │                 │                       │
        │    ┌────────────┴────────────┐          │
        │    ▼                         ▼          │
        │ ┌──────────┐          ┌───────────┐     │
        │ │ Bot ①②   │          │ Web API    │     │ ← 第二層：數據看板
        │ │ Cog 層   │          │ (FastAPI)  │     │
        │ └──────────┘          └───────────┘     │
        │                                         │
        └─────────────────────────────────────────┘
                             ↑
                    第一層：圖論地圖（改寫 combat/shop）
```

---

## 核心機制一：AI Game Master

### 對現有架構的分析

| 現有模組 | 如何被 GM 使用 | 需改動 |
|---------|---------------|--------|
| `database.py` → `get_user()` | GM 組裝玩家狀態 context | 無 |
| `database.py` → `get_inventory()` | GM 知道玩家持有什麼 | 無 |
| `cogs/combat.py` → `_roll_drops`, `_apply_rewards` | GM tool_call `spawn_enemy` 觸發 | 無 |
| `cogs/combat.py` → `compute_damage` | GM 啟動戰鬥時用相同公式 | 無 |
| `cogs/shop.py` → `shop_sell` | GM `modify_currency` 或 `give_item` | 無 |
| `channel_guard.py` | GM 需要知道玩家在哪個頻道（= 目前位置） | 無 |

**關鍵洞察**：現有的資料存取函式已經是 GM 可以直接呼叫的「遊戲原語」。不需要包一層新的 ORM。

### 需要新增的檔案

```
src/
├── gm_context.py       # 組裝 LLM prompt 用的 player + world context
├── gm_tools.py         # 給 LLM 呼叫的強型別工具定義（OpenAI function calling 格式）
├── gm_session.py       # 對話歷史管理（短期記憶）
└── cogs/
    └── gm.py           # /talk 指令 + 專屬頻道攔截器

新增 DB 表：
├── quests              # 任務模板
├── user_quests         # 玩家任務進度
├── reputation          # 陣營聲望
└── world_state         # GM 可寫的全域 key-value
```

### GM 工具定義（OpenAI Function Calling 格式）

```python
GM_TOOLS = [
    {
        "name": "give_item",
        "description": "給予玩家道具",
        "parameters": {
            "user_id": "string",
            "item_name": "string",     # 必須是 items 表中存在的名稱
            "quantity": "integer"
        }
    },
    {
        "name": "modify_currency",
        "description": "增減玩家貨幣",
        "parameters": {
            "user_id": "string",
            "currency": "string",      # an_bi / yi_bi / wu_bi / tuo_bi / bang_bi
            "amount": "integer"        # 正=增加，負=扣除
        }
    },
    {
        "name": "spawn_enemy",
        "description": "在玩家所在頻道生成敵人並啟動戰鬥面板",
        "parameters": {
            "user_id": "string",
            "enemy_name": "string",    # 怪物名稱
            "enemy_hp": "integer",
            "enemy_atk": "integer",
            "enemy_def": "integer",
            "narrative": "string"      # 開場敘述文字
        }
    },
    {
        "name": "start_quest",
        "description": "給予玩家新任務",
        "parameters": {
            "user_id": "string",
            "quest_title": "string",
            "quest_description": "string",
            "objective_type": "string",   # collect / defeat / travel / talk
            "objective_target": "string", # 道具名 / 怪物名 / 節點名
            "objective_count": "integer",
            "reward_items": "object",     # {item_name: qty}
            "reward_currency": "object",  # {currency_name: amount}
        }
    },
    {
        "name": "modify_map",
        "description": "修改地圖狀態（邊權重、節點治安、物資庫存）",
        "parameters": {
            "node_or_edge": "string",
            "target_id": "integer",
            "field": "string",         # danger / security / modifier
            "value": "string",
            "reason": "string"         # 事件原因（記錄用）
        }
    },
    {
        "name": "send_narrative",
        "description": "發送純敘事文字給玩家（不觸發任何機制）",
        "parameters": {
            "user_id": "string",
            "text": "string"
        }
    }
]
```

### Prompt 模板結構

```
System: 你是 PF UTOPIA 的 AI Game Master。
        你操作一個中世紀奇幻世界，包含多個陣營與城鎮。
        你可以呼叫工具函式來實際改變遊戲世界。
        保持角色扮演，不要打破第四面牆。

World State:
  當前全域事件: {world_state}
  活躍玩家數: {online_count}

Player Context:
  名稱: {username}
  位置: {current_node.name}（治安 {node.security}）
  屬性: ATK {atk} DEF {def} HP {hp}
  貨幣: {currencies_summary}
  背包: {inventory_summary}
  進行中任務: {active_quests}
  陣營聲望: {reputation}

  最近事件: {recent_battles}
  
Player Message: {user_input}
```

### 對話流程

```
1. 玩家發送 /talk 或 在 GM 頻道打字
2. gm_context.py 組裝 prompt（從 DB 撈上述欄位）
3. POST LLM API（含 tools 定義）
4. LLM 回傳:
   - 有 tool_calls → 逐一執行，結果餵回 LLM，遞迴最多 3 輪
   - 無 tool_calls → 直接顯示 text
5. 顯示 embed 給玩家（Markdown 渲染 + 像素風邊框）
```

---

## 核心機制二：Web 視覺與數據看板

### 對現有架構的分析

**幾乎純讀取**。現有的 PostgreSQL 資料直接夠用：

| 看板功能 | 需要的查詢 | 現有表 |
|---------|-----------|--------|
| 角色卡 | 玩家屬性 + 貨幣 + 能力評分 | `users` |
| 背包介面 | 道具列表 + 數量 + sell_price | `inventory` JOIN `items` JOIN `shop_sell_prices` |
| 股票走勢圖 | 時間序列價格 | `stock_history`（已有每 15 分一筆） |
| 物資供需面板 | 材料價格 + 漲跌方向 | `shop_sell_prices` |
| 戰績記錄 | 戰鬥勝敗 + 傷害 | `battle_logs` |
| 成就牆 | 解鎖狀態 | `achievements` LEFT JOIN `user_achievements` |
| 排行榜 | TOP 10 排序 | `users` ORDER BY |

**零新資料表**。純讀取層。

### 新增檔案

```
src/api/
├── __init__.py
├── app.py            # FastAPI app 初始化（掛在 Bot 同 event loop）
├── auth.py           # GET /auth/login → Discord OAuth redirect
│                     # GET /auth/callback → JWT 簽發
├── deps.py           # get_current_user() 依賴注入
├── profile.py        # GET /api/me — 角色卡 JSON
├── inventory.py      # GET /api/me/inventory
├── stocks.py         # GET /api/stocks — 6 種股票現價
│                     # GET /api/stocks/:code/history — 歷史價格
├── shop.py           # GET /api/shop — 材料賣價
├── ranking.py        # GET /api/rankings/:category
└── battle.py         # GET /api/me/battles

web/
├── index.html
├── login.html
├── css/
│   └── pixel.css     # image-rendering: pixelated; + 復古色盤
├── js/
│   ├── oauth.js      # Discord OAuth 彈窗流程
│   ├── api.js        # fetch() 封裝 + JWT 自動附加
│   ├── dashboard.js  # 主看板（角色卡 + 背包 + 成就）
│   ├── map.js        # 像素世界地圖（首頁）— Canvas 渲染節點+邊
│   ├── charts.js     # Chart.js 折線圖（股票歷史）
│   └── router.js     # 簡單的 hash-based SPA router
└── assets/
    └── sprites/      # 像素 PNG（節點 icon/角色/道具）
```

### JWT Session 表（唯一新增）

```sql
CREATE TABLE user_sessions (
    discord_id  TEXT PRIMARY KEY REFERENCES users,
    token_hash  TEXT NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL
);
```

只存 hash，不存明文 token。

### 像素風格實作細節

- **首頁即世界地圖**：玩家登入後直接看到像素風 PF UTOPIA 全圖，節點可點擊查看該地區物價、治安、活躍玩家
- Canvas 渲染時故意降低解析度（例：400×300 → 繪製後 scale 2x）
- CSS `image-rendering: pixelated; image-rendering: crisp-edges;`
- 色盤限制 16 色（NES palette）
- 字型：壓縮像素字體（如 Press Start 2P，Google Fonts 免費）
- Discord 頭像用 Canvas 降解析度重繪為 pixel art
- 節點用不同 emoji/sprite 區分類型（🏰 capital / 🌱 wild / ⛪ sanctuary / 💣 arena / 😈 dungeon）
- 道路用像素虛線連接，危險路段紅色閃爍
- 玩家所在節點用發光邊框標示，移動中的玩家顯示沿道路移動的像素小人

---

## 核心機制三：圖論地圖與經濟系統

### 對現有架構的分析

這是**改動最大的層**。以下是詳細影響分析：

#### 需要移除或重構的部分

| 檔案 | 現有內容 | 變更 |
|------|---------|------|
| `settings.json` → `combat_zones` | 5 個平鋪 zone dict | ✂️ 移除，怪物定義移入 `map_nodes` |
| `settings.json` → `dungeon_bosses` | 4 個 Boss dict | 🔄 保留但關聯到特定 node |
| `settings.json` → `world_boss` | 彩虹羊 | 🔄 改為特定 node 上的事件 |
| `settings.json` → `game_params` | 遊戲參數 | ➕ 新增 `travel_speed`, `price_decay_rate` |
| `cogs/combat.py` → `explore()` | 選 zone → 遇敵 → 戰鬥 | 🔄 改為「在 current_node 遇敵」 |
| `cogs/combat.py` | — | ➕ 新增 `move()` 指令 |
| `cogs/shop.py` → `shop_sell_prices` | 全域單一價格 | 🔄 改為 `per_node` 價格 |
| `cogs/shop.py` → `shop_sell()` | — | ➕ 記錄交易量以影響供需 |

#### 不需改動的部分

| 模組 | 原因 |
|------|------|
| `database.py` 資料存取函式 | 只加新函式，不刪舊的 |
| `cogs/combat.py` 的傷害計算 | 公式不變 |
| `cogs/faith.py`, `daily.py`, `social.py` | 與地圖系統無關 |
| `cogs/lottery.py`, `investment.py`, `pet.py` | 經濟層獨立，不受地圖影響 |
| `channel_guard.py` | 頻道 ≠ 地圖節點，兩者平行 |

### 新增資料表

```sql
-- 地圖節點
CREATE TABLE map_nodes (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    node_type       TEXT NOT NULL CHECK (node_type IN ('capital','town','wild','dungeon','sanctuary','arena')),
    faction         TEXT DEFAULT 'neutral',
    security        INTEGER DEFAULT 50 CHECK (security BETWEEN 0 AND 100),
    description     TEXT DEFAULT '',
    enemy_pool      JSONB DEFAULT '[]',    -- 此節點可能出現的怪物
    pos_x           INTEGER,               -- Canvas 渲染用
    pos_y           INTEGER,
    emoji           TEXT DEFAULT '📍'
);

-- 道路邊
CREATE TABLE map_edges (
    id              SERIAL PRIMARY KEY,
    from_node       INTEGER REFERENCES map_nodes ON DELETE CASCADE,
    to_node         INTEGER REFERENCES map_nodes ON DELETE CASCADE,
    base_distance   INTEGER NOT NULL,       -- 基礎移動時間（分鐘）
    base_danger     INTEGER DEFAULT 0,      -- 基礎危險度（影響遇敵率）
    modifiers       JSONB DEFAULT '{}',     -- {"weather": "storm", "event": "monster_raid"}
    UNIQUE (from_node, to_node)
);

-- 節點物資庫存
CREATE TABLE node_inventory (
    node_id         INTEGER REFERENCES map_nodes ON DELETE CASCADE,
    item_id         INTEGER REFERENCES items ON DELETE CASCADE,
    quantity        INTEGER DEFAULT 0,
    demand_rate     REAL DEFAULT 1.0,       -- 需求係數（>1 = 需求高）
    PRIMARY KEY (node_id, item_id)
);

-- 每節點的價格（取代全域 shop_sell_prices）
CREATE TABLE node_prices (
    node_id         INTEGER REFERENCES map_nodes ON DELETE CASCADE,
    item_id         INTEGER REFERENCES items ON DELETE CASCADE,
    current_price   INTEGER NOT NULL,
    base_price      INTEGER NOT NULL,
    direction       TEXT DEFAULT 'flat',
    last_update     TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (node_id, item_id)
);

-- 玩家位置（users 表新增欄位，不用新表）
ALTER TABLE users ADD COLUMN current_node INTEGER REFERENCES map_nodes;
ALTER TABLE users ADD COLUMN travel_target INTEGER REFERENCES map_nodes;
ALTER TABLE users ADD COLUMN travel_start TIMESTAMPTZ;

-- 玩家已探索節點（戰爭迷霧）
CREATE TABLE user_explored (
    user_id         TEXT REFERENCES users ON DELETE CASCADE,
    node_id         INTEGER REFERENCES map_nodes ON DELETE CASCADE,
    explored_at     TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, node_id)
);
```

### 供需定價演算法實作

```
P_next = P_base × (1 + (Demand − Supply) / max(Supply, 1))
```

**每次交易後更新邏輯**：

```python
async def update_node_price(db, node_id, item_id):
    stock = await db.fetchval(
        "SELECT quantity FROM node_inventory WHERE node_id=$1 AND item_id=$2",
        node_id, item_id
    )
    demand = await db.fetchval(
        "SELECT demand_rate FROM node_inventory WHERE node_id=$1 AND item_id=$2",
        node_id, item_id
    )
    base = await db.fetchval("SELECT base_price FROM items WHERE id=$1", item_id)
    
    new_price = int(base * (1 + (demand - stock) / max(stock, 1)))
    new_price = max(new_price, int(base * 0.1))
    new_price = min(new_price, int(base * 10))
    
    await db.execute(
        "UPDATE node_prices SET current_price=$1, last_update=NOW() WHERE node_id=$2 AND item_id=$3",
        new_price, node_id, item_id
    )
```

**跨節點傳導**（BFS 衰減）：

```
當 node A 的某物品價格變動 ΔP：
  對每個相鄰 node B：
    傳導量 = ΔP × 0.3  （距離 1，衰減係數 0.3）
    對 node B 的相鄰 node C：
      傳導量 = ΔP × 0.3 × 0.3 = ΔP × 0.09  （距離 2）
    以此類推，距離 ≥ 4 時停止（0.3^4 ≈ 0.008，可忽略）
```

### 移動系統

```
/move <目標節點>
  1. 檢查目標是否與 current_node 相鄰
  2. 計算 travel_time = edge.base_distance × edge.modifiers.speed_factor
  3. 設定 travel_target, travel_start = NOW()
  4. 定時檢查（每分鐘）：
     if NOW() - travel_start >= travel_time:
       更新 current_node = travel_target
       清除 travel_target
       發送 Discord 通知：「你抵達了 {node.name}」

/move cancel
  取消移動，回到原節點

移動期間 GM 介入：
  edge.base_danger 愈高 → GM 觸發隨機事件機率愈高
  GM 可 tool_call: spawn_enemy / modify_currency / give_item
```

### 種子地圖設計 — PF UTOPIA 世界（13 節點）

沿用原始拓撲，節點名稱統一為安逸烏托邦世界觀：

```
                    [翡翠森林]────[世界魔皇巢穴]
                    /    |    \
        [搗蛋精靈之森]─[初始草原]──[女僕教堂]
            |         |          |
        [大士爺廟] [🏰烏托邦主城]──[競技場]
            |         |          |
        [寵物天堂]  [彩券中心]──[沿海小徑]
                        |
                   [投資交易所]
```

| 節點 | 類型 | 治安 | 對應原始系統 | 特色物資 | 怪物 |
|------|------|------|------------|---------|------|
| 🏰 烏托邦主城 | capital | 90 | 起點、商店、簽到 | 全物資基礎價 | — |
| 🌱 初始草原 | wild | 60 | `/explore` 草原 | 黏液、羊毛（盛產） | 史萊姆、野雞、兔兔、綿羊、鹿、狼、野豬 |
| 🌲 翡翠森林 | wild | 30 | `/explore` 森林 | 皮革、魔石、緞帶（稀有） | 猴子、蛇、哥布林、大蜥蜴、食人魔 |
| 🌊 沿海小徑 | wild | 35 | `/explore` 沿海 | 骨頭、魔石、毒液、緞帶 | 巨蟹、海妖 |
| 😈 世界魔皇巢穴 | dungeon | 5 | `/world_boss` | 緞帶、魔石（大量）、轉法輪 | 彩虹羊（HP 600K） |
| ⛪ 女僕教堂 | sanctuary | 85 | `/pray` `/meditate` | 線香（盛產）、轉法輪 | — |
| 💣 競技場 | arena | 70 | `/arena` | 骨頭、皮革 | 其他玩家 |
| 🍬 搗蛋精靈之森 | wild | 40 | 精靈供奉 | 糖果、毒液 | 搗蛋精靈（初/中/高） |
| 🎟 彩券中心 | town | 80 | `/lottery_*` | — | — |
| 📊 投資交易所 | town | 75 | `/market` `/invest_*` | — | — |
| 🏯 大士爺廟 | sanctuary | 80 | 節慶活動 | 糖果、轉法輪 | — |
| 🥏 寵物天堂 | wild | 50 | `/pet_battle` | 寵物 EXP | 野生寵物 |

### 玩家視角差異化

同一張地圖，每位玩家看到的不同：

| 機制 | 說明 |
|------|------|
| **戰爭迷霧** | 未到訪的節點呈灰色 `???`，抵達後解鎖 |
| **當前位置** | 玩家所在節點像素發光邊框，其他節點可看到同區域玩家數量 |
| **個人標記** | 進行中的任務目標節點顯示 `!` 驚嘆號 |
| **聲望著色** | 根據該玩家對各節點陣營的聲望，邊框顏色變化（綠=友好、紅=敵對） |
| **已知物價** | 僅顯示已解鎖節點的物資價格，未解鎖節點不揭露 |
| **移動中** | 正在移動的玩家顯示像素小人沿道路移動，其他玩家可看到「路上有人」但不知是誰 |

### 地圖 API 端點（player-specific）

```
GET /api/map
  → 回傳該玩家視角的完整地圖 JSON：
    {
      nodes: [{id, name, type, unlocked, current_players, security, quest_marker}],
      edges: [{from, to, distance, danger, traveled}],
      my_position: {node_id, traveling: {target, eta}}
    }
```

> 節點數量：初始 13 個，AI GM 可動態擴充（節慶活動、新區域開放）。

---

## 三機制相依關係

```
         ┌──────────────┐
         │  圖論地圖     │ ← 基礎層：改寫 combat + shop
         └──────┬───────┘
                │ 提供 node/edge 資料
    ┌───────────┼───────────┐
    ▼           ▼           ▼
┌───────┐  ┌───────┐  ┌───────────┐
│ AI GM │  │Web 看板│  │ 經濟模擬   │
│       │  │       │  │ (可獨立)   │
└───┬───┘  └───────┘  └───────────┘
    │ GM 讀寫 node_inventory
    │ GM 讀寫 edge.modifiers
    │ GM 觸發 spawn_enemy（使用 node.enemy_pool）
    │ GM 發放 quest（目標節點來自 map_nodes）
    ▼
  quests / reputation / world_state
```

**開發順序建議**：
1. 圖論地圖（改寫既有 combat + shop，再加 node 系統）
2. Web 看板（純讀取，可在步驟 1 進行中並行開發）
3. AI GM（需要步驟 1 完成後才有 node/edge 資料可用）

---

## 實作前必須先確認的設計決策

| 決策 | 選項 |
|------|------|
| LLM 提供者 | OpenAI (GPT-4o) / Anthropic (Claude) / 本地模型 |
| 前端框架 | 純 HTML+JS / React / Svelte |
| 地圖渲染 | Canvas 手繪 / Leaflet 改像素主題 |
| 移動速度 | 每距離單位 = 1 分鐘 / 可配置 |
| 節點數量 | 初始 12 個 / 後續由 GM 動態生成 |

---

> 此文件為規劃用途。所有內容尚未實作，等待明確指令後開始。  
> 現有穩定版本詳見 `note/architecture.md`
