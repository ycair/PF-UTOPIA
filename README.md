# PF UTOPIA — 安逸烏托邦 Discord 遊戲機器人

兩隻 Discord Bot 驅動的完整 MMORPG 文字遊戲，內建戰鬥、經濟、彩券、投資、寵物等系統。

## 架構

```
Bot ① 安逸烏托邦專用女僕①號 (36 指令)     Bot ② 安逸烏托邦專用女僕②號 (19 指令)
├── /register    註冊                      ├── /shop         商店
├── /profile     角色檔案                  ├── /shop_buy     購買道具
├── /daily       每日簽到                  ├── /shop_sell    出售材料
├── /explore     野區探索                  ├── /lottery_*    彩券系統
├── /dungeon     副本 Boss                 ├── /market       股市行情
├── /altar       主線祭壇                  ├── /invest_*     股票交易
├── /world_boss  世界魔皇                  ├── /pet_*        寵物系統
├── /pray        膜拜教堂                  ├── /achievements 成就
├── /meditate    坐禪修行                  ├── /rank         排行榜
├── /ability     能力分配                  ├── /wyr          你寧可
├── /hug /kiss ... 社交互動               └── /event        活動
└── /vote /dice ... 工具指令
```

## 技術棧

| 項目 | 技術 |
|------|------|
| 語言 | Python 3.13 |
| Discord | discord.py 2.7 |
| 資料庫 | PostgreSQL 16 + asyncpg |
| 指令 | Slash Commands |
| 配置 | 熱重載 JSON（`settings.json`） |
| 儲值 | Buy Me a Coffee Webhook（規劃中） |

## 快速開始

### 環境需求
- Python 3.13+
- PostgreSQL 16
- Discord Bot Token ×2（[Developer Portal](https://discord.com/developers/applications)）

### 安裝

```bash
git clone https://github.com/ycair/PF-UTOPIA.git
cd YCAIR-DCBOT
python3 -m venv .venv
source .venv/bin/activate
pip install discord.py asyncpg aiohttp
```

### 設定

```bash
cp src/config.template.py src/config.py
# 編輯 src/config.py，填入 Bot Token 和 Guild ID
```

或使用環境變數：
```bash
export BOT1_TOKEN="your-token"
export BOT2_TOKEN="your-token"
export GUILD_ID="921725752796393483"
export UTOPIA_DB_URL="postgresql://localhost:5432/utopia"
```

### 資料庫

```bash
createdb utopia
```

Bot 啟動時自動建立表格與種子資料。

### 啟動

```bash
# Bot ①（RPG 核心 + 管理）
python bot1_main.py

# Bot ②（經濟 + 活動）- 另一個終端
python bot2_main.py
```

### 熱重載

修改 `settings.json` 後**無需重啟** — 頻道限制、怪物數值、遊戲平衡全部即時生效。

## 遊戲系統

| 系統 | 說明 |
|------|------|
| ⚔️ 戰鬥 | 5 個野區 + 4 個副本 Boss + 主線祭壇 + 世界魔皇 |
| 💰 經濟 | 5 種貨幣（安幣/逸幣/烏幣/托幣/邦幣），動態商店價格 |
| 🎟 彩券 | 手動/自動選號、VIP加成、兌獎 |
| 📊 投資 | 6 種股票，每 15 分鐘價格波動 |
| 🔆 寵物 | 抽卡、養成、出戰加成 |
| 🏆 成就 | 11 種成就，自動追蹤進度 |
| 🛐 信仰 | 膜拜教堂 + 坐禪修行 |
| 📝 簽到 | 每日簽到，連續加成，月卡系統 |

## 專案結構

```
├── bot1_main.py          # Bot ① 入口
├── bot2_main.py          # Bot ② 入口
├── settings.json         # 熱重載配置（頻道/戰鬥/平衡）
├── note/
│   └── architecture.md   # 技術規格書
└── src/
    ├── config.py          # Token、DB（不入版控）
    ├── config.template.py # 設定檔範本
    ├── database.py        # PostgreSQL 層
    ├── hotconfig.py       # 熱重載管理器
    ├── channel_guard.py   # 頻道限制
    ├── bmc_webhook.py     # Buy Me a Coffee 接收端
    └── cogs/
        ├── registration.py    # 註冊
        ├── profile.py         # 角色檔案
        ├── daily.py           # 簽到
        ├── inventory.py       # 背包
        ├── combat.py          # 戰鬥
        ├── faith.py           # 信仰
        ├── stats_ability.py   # 能力
        ├── social.py          # 社交
        ├── utility.py         # 工具
        ├── shop.py            # 商店
        ├── lottery.py         # 彩券
        ├── investment.py      # 投資
        ├── pet.py             # 寵物
        ├── achievements.py    # 成就
        ├── ranking.py         # 排行
        └── events.py          # 活動
```

## 詳細文件

參見 [`note/architecture.md`](note/architecture.md) — 包含完整資料庫 Schema、戰鬥公式、經濟參數、指令對照表。

## License

MIT
