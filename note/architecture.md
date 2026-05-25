# PF UTOPIA 安逸烏托邦 — 技術規格書

## 一、系統架構總覽

```
伺服器：PF UTOPIA 安逸烏托邦 (ID: 921725752796393483)
├── Bot ① 號：安逸烏托邦專用女僕①號 (ID: 921779959717048340)
│   └── 職責：RPG 核心 + 管理工具 + 社交互動
├── Bot ② 號：安逸烏托邦專用女僕②號 (ID: 868902710831890432)
│   └── 職責：經濟系統 + 活動 + 彩券 + 投資 + 寵物
└── 資料庫：PostgreSQL 16 (utopia)
```

## 二、頻道限制體系

每個指令只能在指定的 Discord 頻道中使用，還原原始遊戲設計。

### 2.1 頻道 ID 對照表

| 頻道 Key | 頻道 ID | 說明 | 隸屬類別 |
|----------|---------|------|---------|
| register | 969825727371423755 | 🚧伺服器註冊 | 烏托邦冒險 |
| bag | 968157417789595709 | 🛒 道具商店 / 背包 | 烏托邦冒險 |
| daily | 969830297032097802 | 📝每日簽到 | 烏托邦冒險 |
| shop | 969879138271891486 | 🛒 道具商店 | 商店、抽卡 |
| chest | 945683117644079194 | 🎁寶箱領取處 | 烏托邦冒險 |
| lottery | 953514247755821076 | 🈲彩券記錄 | 彩券 |
| lottery_result | 953514184279224360 | 🎊彩券開獎 | 彩券 |
| vote | 922114373915402301 | 🎰投票或抽獎 | 伺服器大廳 |
| important_vote | 921727644150693928 | ❗重要投票項目 | 伺服器大廳 |
| main_room | 921925385225125898 | 🏬主房間 | 神奇討論區 |
| sub_room | 985372968525463582 | ⛺副房間 | 神奇討論區 |
| nsfw | 921751363157884988 | 🔞真的母湯 | 神奇討論區 |
| profile | 968129867875577896 | 📊個人資料查詢 | 烏托邦冒險 |
| combat | 968157417789595709 | 戰鬥類指令 | 烏托邦冒險 |
| pray | 968178531248799775 | ⛪膜拜教堂 | 烏托邦冒險 |
| meditate | 968178888126001152 | 🧘坐禪修行 | 烏托邦冒險 |
| arena | 968180073492340767 | 💣競技場 | 經典冒險 |
| altar | 968180512345678901 | 🔮主線祭壇 | 經典冒險 |
| world_boss | 968181234567890123 | 😈世界魔皇 | 經典冒險 |
| invest | 968182345678901234 | 💰投資交易所 | 投資交易所 |
| pet | 968183456789012345 | 🔆寵物抽卡 | 商店、抽卡 |
| pet_heaven | 968184567890123456 | 🥏寵物的天堂 | 經典冒險 |
| admin | 921726467562684476 | 💻管理後台 | 管理51區 |
| test | 921726556337623071 | 🚧測試 | 境外測試 |

### 2.2 指令 → 頻道限制對應表

#### 無限制指令（可在任何頻道使用）
這些是社交/工具性質，不會產生大量訊息干擾：

- `/register` — 註冊（即使標為無限制，實際上需要配合頻道內的說明訊息引導玩家到正確頻道）
- `/hug`, `/kiss`, `/pat`, `/slap`, `/kill`, `/wink` — 社交互動
- `/avatar` — 取得頭像
- `/ping` — 延遲查詢
- `/divider` — 分隔線
- `/iwin` — 梗指令
- `/rps` — 剪刀石頭布（簡短互動）
- `/nickname` — 更改暱稱
- `/dm_me` — 私訊請求

#### 需要特定頻道的指令

**RPG 核心 (Bot ①)**
| 指令 | 限制頻道 Key | 頻道 ID |
|------|-------------|---------|
| `/profile` | profile | 968129867875577896 |
| `/daily` | daily | 969830297032097802 |
| `/bag` | bag | 968157417789595709 |
| `/explore` | combat | 968157417789595709 |
| `/dungeon` | combat | 968157417789595709 |
| `/altar` | altar | 968180512345678901 |
| `/world_boss` | world_boss | 968181234567890123 |
| `/arena` | arena | 968180073492340767 |
| `/pray` | pray | 968178531248799775 |
| `/meditate` | meditate | 968178888126001152 |
| `/ability` | profile | 968129867875577896 |
| `/draw_lots` | vote | 922114373915402301 |
| `/dice` | main_room | 921925385225125898 |
| `/guess_number` | main_room | 921925385225125898 |
| `/slot` | main_room | 921925385225125898 |
| `/answer_book` | main_room | 921925385225125898 |
| `/yesno` | main_room | 921925385225125898 |
| `/vote_create` | vote | 922114373915402301 |
| `/clean` | admin | 921726467562684476 |
| `/anon` | admin | 921726467562684476 |
| `/gif_nsfw` | nsfw | 921751363157884988 |

**經濟系統 (Bot ②)**
| 指令 | 限制頻道 Key | 頻道 ID |
|------|-------------|---------|
| `/shop` | shop | 969879138271891486 |
| `/shop_buy` | shop | 969879138271891486 |
| `/shop_sell` | shop | 969879138271891486 |
| `/use` | bag | 968157417789595709 |
| `/lottery_buy` | lottery | 953514247755821076 |
| `/lottery_auto` | lottery | 953514247755821076 |
| `/lottery_vip` | lottery | 953514247755821076 |
| `/lottery_check` | lottery | 953514247755821076 |
| `/market` | invest | 968182345678901234 |
| `/invest_buy` | invest | 968182345678901234 |
| `/invest_sell` | invest | 968182345678901234 |
| `/invest_portfolio` | invest | 968182345678901234 |
| `/pet_gacha` | pet | 968183456789012345 |
| `/pet_list` | pet | 968183456789012345 |
| `/pet_equip` | pet | 968183456789012345 |
| `/pet_battle` | pet_heaven | 968184567890123456 |
| `/achievements` | profile | 968129867875577896 |
| `/rank` | profile | 968129867875577896 |
| `/wyr` | main_room | 921925385225125898 |
| `/event` | main_room | 921925385225125898 |

### 2.3 頻道檢查實作機制

每個 Cog 的指令在執行前檢查 `interaction.channel.id`。若不在允許的頻道中，回覆提示訊息告知正確頻道。

```
🔴 不可在未授權之頻道使用該指令
請前往 <#頻道ID> 使用此功能
```

## 三、PostgreSQL 資料庫結構

### 3.1 連線設定

| 參數 | 值 |
|------|-------|
| Host | localhost:5432 |
| Database | utopia |
| 連線池大小 | min=2, max=10 |
| 驅動 | asyncpg 0.31 |

### 3.2 資料表清單與詳細欄位

#### `users` — 玩家核心資料

| 欄位 | SQL 型別 | 預設值 | 說明 |
|------|---------|--------|------|
| `discord_id` | TEXT PK | — | Discord 用戶 ID |
| `username` | TEXT NOT NULL | — | 玩家暱稱 |
| `registered_at` | TIMESTAMPTZ | NOW() | 註冊時間 |
| `stamina` | INTEGER | 150 | 當前體力 |
| `max_stamina` | INTEGER | 150 | 體力上限（可透過道具提升） |
| `yuan_shen` | INTEGER | 0 | 元神（特殊能量，用途待擴充） |
| `xiu_wei` | INTEGER | 0 | 修為（坐禪/膜拜累積） |
| `xian_xiang` | INTEGER | 0 | 線香數量（膜拜消耗品） |
| `chat_level` | INTEGER | 0 | 聊天等級 (0~N) |
| `chat_exp` | DOUBLE PRECISION | 0.0 | 當前聊天經驗值 |
| `chat_exp_next` | DOUBLE PRECISION | 50.0 | 升等所需經驗值（隨等級成長） |
| `attack` | INTEGER | 10 | 攻擊力 |
| `defense` | INTEGER | 5 | 防禦力 |
| `hp` | INTEGER | 100 | 血量上限 |
| `ability_points` | INTEGER | 0 | 未分配能力點 |
| `an_bi` | INTEGER | 0 | 🪙 安幣（簽到獎勵、戰鬥獎勵） |
| `yi_bi` | INTEGER | 0 | 💵 逸幣（月卡獎勵、高級貨幣） |
| `wu_bi` | INTEGER | 0 | 💶 烏幣（精靈供奉、活動獎勵） |
| `tuo_bi` | INTEGER | 0 | 💴 托幣（賣材料獲得、主要交易貨幣） |
| `bang_bi` | INTEGER | 0 | 💷 邦幣（稀有貨幣，極稀有活動） |
| `monthly_card` | TEXT | NULL | 月卡類型：`gold` / `diamond` / NULL |
| `monthly_expiry` | DATE | NULL | 月卡到期日 |
| `signin_streak` | INTEGER | 0 | 連續簽到天數 |
| `last_signin` | DATE | NULL | 上次簽到日期 |
| `candy` | INTEGER | 0 | 🍬 糖果數量（供奉精靈） |

##### 能力評分計算公式

```
能力評分 = attack × 100 + defense × 50 + hp × 10
初始能力評分 = 10×100 + 5×50 + 100×10 = 2250
```

##### 聊天經驗值升級曲線

```
Lv 0: chat_exp_next = 50
Lv 1: chat_exp_next = 83
Lv 2: chat_exp_next = 105
Lv 3+: chat_exp_next = 50 + level × 15
```

每條伺服器訊息（非指令）獲得 2~5 點經驗值。

#### `items` — 道具定義

| 欄位 | SQL 型別 | 說明 |
|------|---------|------|
| `id` | SERIAL PK | 道具編號 |
| `name` | TEXT UNIQUE NOT NULL | 道具名稱 |
| `description` | TEXT | 道具敘述 |
| `item_type` | TEXT | `material` / `consumable` |
| `rarity` | TEXT | `common` / `uncommon` / `rare` / `epic` / `legendary` |
| `base_price` | INTEGER | 材料基礎賣價（托幣）— 浮動基準值 |
| `buy_price` | INTEGER | 商店購買價（安幣）— 消耗品固定購買價；材料此值為參考價 |
| `emoji` | TEXT | 顯示用 emoji |

##### 種子道具資料

| # | 名稱 | 類型 | 稀有度 | base_price | buy_price | emoji | 取得方式 |
|---|------|------|--------|------------|-----------|-------|---------|
| 1 | 黏液 | material | common | 5 | — | 🫧 | 草原外圍：史萊姆 |
| 2 | 羽毛 | material | common | 7 | — | 🪶 | 草原外圍：野雞 |
| 3 | 肉 | material | common | 12 | — | 🥩 | 草原：野雞/兔兔/鹿/野豬 |
| 4 | 羊毛 | material | common | 13 | — | 🧶 | 草原：兔兔/綿羊 |
| 5 | 骨頭 | material | common | 10 | — | 🦴 | 草原/森林：野豬/猴子/哥布林 |
| 6 | 牙齒 | material | uncommon | 11 | — | 🦷 | 草原/森林：狼/猴子/大蜥蜴 |
| 7 | 皮革 | material | uncommon | 16 | — | 🪵 | 草原/森林：鹿/狼/蛇/大蜥蜴 |
| 8 | 緞帶 | material | rare | 50000 | — | 🎀 | 高級 Boss/森林內部極稀有 |
| 9 | 毒液 | material | rare | 48 | — | 🧪 | 森林：蛇/海妖 |
| 10 | 魔石 | material | epic | 180 | — | 💎 | 中高級 Boss/哥布林/食人魔 |
| 11 | 恢復劑 | consumable | common | — | 100 | 🧃 | 商店購買（托幣），恢復 50 體力 + 50 HP |
| 12 | 強效恢復劑 | consumable | uncommon | — | 300 | 🧋 | 商店購買（托幣），恢復 150 體力 + 150 HP |
| 13 | 線香 | consumable | common | — | 50 | 🕯️ | 商店購買 / Boss 掉落 |
| 14 | 糖果 | consumable | common | — | 30 | 🍬 | 商店購買 |
| 15 | 轉法輪 | consumable | rare | — | 500 | ☸️ | 高級 Boss 掉落 / 商店購買 |

##### 價格策略

| 價格類型 | 機制 | 適用道具 |
|---------|------|---------|
| **賣價** (shop_sell_prices) | 每 30 分鐘 ±15% 隨機波動，範圍 = base_price × 0.3 ~ base_price × 3 | 材料 (material) |
| **買價** (items.buy_price) | 固定價格，預留 `event_discount` 活動折扣欄位 | 消耗品 (consumable) |

#### `inventory` — 玩家背包

| 欄位 | 說明 |
|------|------|
| `user_id` TEXT FK → users | 玩家 ID |
| `item_id` INTEGER FK → items | 道具 ID |
| `quantity` INTEGER | 持有數量 |

#### `shop_sell_prices` — 材料賣價（動態）

| 欄位 | 說明 |
|------|------|
| `item_id` INTEGER PK FK | 道具 ID（僅 material） |
| `current_price` INTEGER | 當前賣價 |
| `direction` TEXT | 價格趨勢：`up` / `down` / `flat` |
| `last_update` TIMESTAMPTZ | 上次更新時間 |

#### `lottery_rounds` — 彩券期數

| 欄位 | 說明 |
|------|------|
| `round_id` SERIAL PK | 期數編號 |
| `numbers` INTEGER[] (6) | 開獎號碼（1~49，6 個） |
| `drawn_at` TIMESTAMPTZ | 開獎時間 |
| `status` TEXT | `open` / `drawn` |

#### `lottery_tickets` — 彩券投注

| 欄位 | 說明 |
|------|------|
| `id` SERIAL PK | — |
| `round_id` INTEGER FK | 期數 |
| `user_id` TEXT FK | 玩家 |
| `numbers` INTEGER[] (6) | 選號 |
| `is_vip` BOOLEAN | 是否 VIP 加成票 |
| `is_auto` BOOLEAN | 是否自動選號 |
| `purchased_at` TIMESTAMPTZ | 購買時間 |

##### 彩券規則
- 號碼範圍：1~49
- 每張票價格：500 安幣（普通）/ 1000 安幣（VIP）
- 開獎方式：隨機選 6 + 1（特別號）
- 中獎獎金以安幣發放，VIP 票獎金 ×2

#### `stocks` — 股票定義

| 欄位 | 說明 |
|------|------|
| `id` SERIAL PK | — |
| `code` TEXT UNIQUE | 股票代碼 |
| `name` TEXT | 股票名稱 |
| `current_price` INTEGER | 當前價格（托幣） |
| `emoji` TEXT | 顯示 emoji |
| `volatility` DOUBLE PRECISION | 波動率（每 15 分鐘） |

| 代碼 | 名稱 | 初始價 | 波動率 | emoji |
|------|------|--------|--------|-------|
| bronze_turtle | 青銅烏龜 | 1,700 | 5% | 🐢 |
| silver_turtle | 白銀烏龜 | 1,250 | 6% | 🐢 |
| gold_turtle | 黃金烏龜 | 17,000 | 4% | 🐢 |
| diamond_turtle | 鑽石烏龜 | 3,500,000 | 3% | 💎 |
| stone_turtle | 石頭烏龜 | 10 | 10% | 🪨 |
| ruby_turtle | 紅寶石烏龜 | 800,000 | 4% | 💠 |

##### 投資規則
- 每 15 分鐘自動更新價格：`new = current × (1 + random(-vol, +vol))`
- 最低價不低於初始價的 10%（防歸零）
- 記錄所有歷史價格於 `stock_history`

#### `user_stocks` — 玩家持股

| 欄位 | 說明 |
|------|------|
| `user_id` TEXT FK | 玩家 ID |
| `stock_id` INTEGER FK | 股票 ID |
| `quantity` INTEGER | 持有股數 |
| `avg_cost` INTEGER | 平均購入成本 |

#### `stock_history` — 股票價格歷史

| 欄位 | 說明 |
|------|------|
| `id` SERIAL PK | — |
| `stock_id` INTEGER FK | 股票 ID |
| `price` INTEGER | 價格 |
| `recorded_at` TIMESTAMPTZ | 記錄時間 |

#### `battle_logs` — 戰鬥記錄

| 欄位 | 說明 |
|------|------|
| `id` SERIAL PK | — |
| `user_id` TEXT FK | 玩家 ID |
| `zone` TEXT | 區域名稱 |
| `enemy` TEXT | 敵人名稱 |
| `result` TEXT | `win` / `lose` |
| `turns` INTEGER | 總回合數 |
| `damage_dealt` DOUBLE PRECISION | 總造成傷害 |
| `damage_taken` DOUBLE PRECISION | 總承受傷害 |
| `rewards` JSONB | `{items: [{name, qty}, ...], currencies: {an_bi: N, tuo_bi: N, ...}}` |
| `battled_at` TIMESTAMPTZ | 戰鬥時間 |

#### `achievements` — 成就定義

| 欄位 | 說明 |
|------|------|
| `id` SERIAL PK | — |
| `name` TEXT UNIQUE | 成就名稱 |
| `description` TEXT | 達成條件描述 |
| `category` TEXT | 分類：`general` / `daily` / `combat` / `economy` / `investment` / `pet` / `lottery` |
| `required_value` INTEGER | 達成所需數值 |

| 成就 | 類別 | 條件 |
|------|------|------|
| 初來乍到 | general | 完成註冊 |
| 簽到新手 | daily | 累積簽到 7 天 |
| 簽到達人 | daily | 累積簽到 30 天 |
| 簽到狂人 | daily | 累積簽到 100 天 |
| 初次戰鬥 | combat | 完成第一次戰鬥 |
| 百戰勇士 | combat | 戰鬥勝利 100 次 |
| 富豪之路 | economy | 持有安幣 ≥ 100,000 |
| 百萬富翁 | economy | 持有安幣 ≥ 1,000,000 |
| 投資新手 | investment | 完成第一次股票買賣 |
| 寵物大師 | pet | 抽到傳說級寵物 |
| 彩券幸運兒 | lottery | 彩券中獎 |

#### `user_achievements` — 玩家成就

| 欄位 | 說明 |
|------|------|
| `user_id` TEXT FK | 玩家 ID |
| `achievement_id` INTEGER FK | 成就 ID |
| `achieved_at` TIMESTAMPTZ | 解鎖時間 |

#### `arena_records` — 競技場戰績

| 欄位 | 說明 |
|------|------|
| `user_id` TEXT PK FK | 玩家 ID |
| `wins` INTEGER | 勝場數 |
| `losses` INTEGER | 敗場數 |
| `rank_points` INTEGER | 排名點數（初始 1000） |

#### `pets` — 寵物定義

| 欄位 | 說明 |
|------|------|
| `id` SERIAL PK | — |
| `name` TEXT UNIQUE | 寵物名稱 |
| `rarity` TEXT | `legendary` / `rare` / `uncommon` |
| `attack_bonus` INTEGER | 攻擊加成 |
| `defense_bonus` INTEGER | 防禦加成 |
| `hp_bonus` INTEGER | 血量加成 |
| `emoji` TEXT | 顯示 emoji |

| 名稱 | 稀有度 | ATK+ | DEF+ | HP+ | 抽中率 | emoji |
|------|--------|------|------|-----|--------|-------|
| 教主 | legendary | 15 | 8 | 30 | 1% | 👑 |
| 灰啾啾 | rare | 8 | 3 | 10 | 3.8% | 🐦 |
| 胖柴 | rare | 4 | 7 | 12 | 3.8% | 🐕 |
| 灰吱吱 | rare | 6 | 4 | 8 | 3.8% | 🐭 |
| 啾太郎 | uncommon | 5 | 5 | 5 | 3.8% | 🐤 |

##### 寵物系統規則
- 寵物抽卡：每抽 500 逸幣
- 每隻寵物可升級（戰鬥累積經驗）
- 同一時間只能出戰 1 隻寵物（is_active = true）
- 寵物天堂：寵物專屬戰鬥區域

#### `user_pets` — 玩家寵物

| 欄位 | 說明 |
|------|------|
| `user_id` TEXT FK | 玩家 ID |
| `pet_id` INTEGER FK | 寵物 ID |
| `level` INTEGER | 等級（初始 1） |
| `exp` INTEGER | 經驗值 |
| `is_active` BOOLEAN | 是否出戰中 |
| `obtained_at` TIMESTAMPTZ | 獲得時間 |

#### `signin_logs` — 簽到記錄

| 欄位 | 說明 |
|------|------|
| `user_id` TEXT | 玩家 ID |
| `signin_date` DATE | 簽到日期 |
| `streak` INTEGER | 當天連續簽到數 |
| `reward_an_bi` INTEGER | 安幣獎勵 |
| `reward_yi_bi` INTEGER | 逸幣獎勵（月卡） |

#### `anon_messages` — 匿名留言

| 欄位 | 說明 |
|------|------|
| `id` SERIAL PK | — |
| `user_id` TEXT FK | 發送者 ID |
| `content` TEXT | 留言內容 |
| `sent_at` TIMESTAMPTZ | 發送時間 |

## 四、戰鬥系統詳細參數

### 4.1 傷害計算公式

```
玩家攻擊力 = base_attack + active_pet.attack_bonus + equipment_atk_bonus
玩家防禦力 = base_defense + active_pet.defense_bonus + equipment_def_bonus
玩家血量   = base_hp + active_pet.hp_bonus + equipment_hp_bonus

玩家造成傷害 = max(1, (玩家攻擊力 - 敵方防禦力 × 0.5) × random(0.8, 1.2))
敵方造成傷害 = max(1, (敵方攻擊力 - 玩家防禦力 × 0.5) × random(0.8, 1.2))

能力評分 = attack × 100 + defense × 50 + hp × 10
```

### 4.2 野區（消耗體力探索）

| 區域 Key | 名稱 | 消耗體力 | 怪物 |
|-----------|------|---------|------|
| initial_grassland_outer | 初始草原外圍 | 8 | 史萊姆、野雞、兔兔、綿羊 |
| initial_grassland_inner | 初始草原內部 | 10 | 鹿、狼、野豬 (+外圍罕見怪) |
| jade_forest_outer | 翡翠森林外圍 | 12 | 猴子、蛇、哥布林 |
| jade_forest_inner | 翡翠森林內部 | 15 | 大蜥蜴、食人魔 (+外圍罕見怪) |
| coastal_path | 沿海小徑 | 14 | 巨蟹、海妖 |

#### 初始草原外圍 怪物詳細

| 怪物 | HP | ATK | DEF | 掉落物 | 出現機率 |
|------|-----|-----|-----|--------|---------|
| 史萊姆 | 5 | 1 | 0 | 黏液(1~3, 80%) | 30% |
| 野雞 | 8 | 2 | 1 | 羽毛(1~2, 70%), 肉(1, 30%) | 25% |
| 兔兔 | 6 | 1 | 0 | 肉(1~2, 50%), 羊毛(1, 30%) | 25% |
| 綿羊 | 10 | 1 | 2 | 羊毛(2~4, 80%) | 20% |

#### 初始草原內部 怪物詳細

| 怪物 | HP | ATK | DEF | 掉落物 | 出現機率 |
|------|-----|-----|-----|--------|---------|
| 史萊姆[罕見] | 8 | 2 | 1 | 黏液(2~5, 80%) | 5% |
| 野雞[罕見] | 12 | 3 | 2 | 羽毛(2~4, 70%) | 5% |
| 兔兔[罕見] | 10 | 2 | 1 | 肉(2~4, 50%) | 5% |
| 綿羊[罕見] | 15 | 2 | 3 | 羊毛(3~6, 80%) | 5% |
| 鹿 | 20 | 4 | 2 | 肉(2~3, 60%), 皮革(1~2, 40%) | 20% |
| 狼 | 25 | 6 | 2 | 牙齒(1~2, 50%), 皮革(1, 30%) | 30% |
| 野豬 | 30 | 5 | 4 | 肉(3~5, 70%), 骨頭(1~2, 50%) | 30% |

#### 翡翠森林外圍 怪物詳細

| 怪物 | HP | ATK | DEF | 掉落物 | 出現機率 |
|------|-----|-----|-----|--------|---------|
| 猴子 | 35 | 7 | 3 | 骨頭(1~2, 60%), 牙齒(1, 40%) | 35% |
| 蛇 | 30 | 8 | 2 | 毒液(1~2, 50%), 皮革(1, 30%) | 30% |
| 哥布林 | 40 | 9 | 3 | 魔石(1, 30%), 骨頭(1~3, 60%) | 35% |

#### 翡翠森林內部 怪物詳細

| 怪物 | HP | ATK | DEF | 掉落物 | 出現機率 |
|------|-----|-----|-----|--------|---------|
| 猴子[罕見] | 50 | 10 | 5 | 骨頭(2~4, 60%) | 8% |
| 蛇[罕見] | 45 | 11 | 3 | 毒液(2~4, 50%) | 8% |
| 哥布林[罕見] | 55 | 12 | 4 | 魔石(1~2, 40%) | 8% |
| 大蜥蜴 | 70 | 14 | 6 | 皮革(2~4, 50%), 牙齒(1~3, 40%) | 38% |
| 食人魔 | 90 | 16 | 5 | 魔石(2~3, 40%), 緞帶(1, 5%) | 38% |

#### 沿海小徑 怪物詳細

| 怪物 | HP | ATK | DEF | 掉落物 | 出現機率 |
|------|-----|-----|-----|--------|---------|
| 巨蟹 | 55 | 12 | 7 | 骨頭(2~3, 50%), 魔石(1~2, 30%) | 55% |
| 海妖 | 60 | 13 | 4 | 毒液(2~3, 50%), 緞帶(1, 8%) | 45% |

### 4.3 副本 Boss

| 副本 Key | 名稱 | 體力 | 建議戰力 | 完美戰力 | HP | ATK | DEF | 掉落 |
|----------|------|------|---------|---------|-----|-----|-----|------|
| zombie | 征服入侵殭屍 | 10 | 2,800 | 3,000 | 120 | 10 | 5 | 骨頭(3~6,80%), 魔石(1~2,40%), 線香(1~3,60%) |
| army | 征服入侵軍團 | 30 | 24,300 | 27,000 | 400 | 25 | 15 | 皮革(3~6,70%), 魔石(2~4,50%), 線香(2~5,60%) |
| maid_ribbon | 解開女僕的緞帶 | 50 | 218,700 | 243,000 | 2,000 | 60 | 40 | 緞帶(1~3,60%), 魔石(3~7,50%), 轉法輪(1~2,30%) |
| maid_ribbons | 解開女僕們的緞帶 | 70 | 1,749,600 | 2,187,000 | 8,000 | 150 | 100 | 緞帶(3~8,70%), 魔石(5~12,50%), 轉法輪(2~5,40%) |

##### Boss 戰鬥特殊規則
- 戰力低於建議戰力 70%：無法挑戰
- 戰力在建議~完美之間：正常傷害
- 戰力超過完美戰力：傷害 ×1.2 加成

### 4.4 世界魔皇 — 彩虹羊

| 參數 | 值 |
|------|-----|
| HP | 600,000（全域共用） |
| ATK | 20 |
| DEF | 50 |
| 每次挑戰消耗體力 | 15 |
| 討伐成功獎勵 | 全體參與者依傷害比例分配獎勵 |
| HP 重置 | 每 24 小時或擊殺後重置 |

### 4.5 持久血量與死亡系統

血量跨戰鬥持久保留在 `current_hp` 欄位，不會自動刷新。

| 參數 | 值 |
|------|-----|
| 初始血量 | `current_hp = hp`（滿血） |
| 受傷 | 戰鬥中承受的傷害直接扣減 `current_hp` |
| 陣亡 | `current_hp ≤ 0`，無法戰鬥 |
| 復活費用 | 1,500 托幣（`/revive`） |
| 復活效果 | 出生於烏托邦主城，滿血 |

**三種回血方式**：

| 方式 | 效果 |
|------|------|
| 🏰 回到主城 | 自動滿血（`travel_check_loop` 觸發） |
| 🙏 大士爺廟膜拜 | `current_hp = hp`（滿血） |
| 🧃 恢復劑 / 強效恢復劑 | +50 / +150 HP（不超過 `hp` 上限） |

**Profile 保護狀態顯示**：

| 節點 | 顯示 |
|------|------|
| 烏托邦主城 | 🛡️ 主城保護：不受傷害 |
| 大士爺廟 | 🛡️ 鬼王庇佑：不受傷害 |
| 其他安全節點 | 🛡️ 安全區域 |

### 4.6 競技場 PvP

| 參數 | 值 |
|------|-----|
| 挑戰限制 | 對手必須在線（需確認）或至少已註冊 |
| 初始排名點數 | 1,000 |
| 勝利 | +25 點 |
| 失敗 | -15 點 |
| 傷害計算 | 與野區相同公式 |

### 4.7 信仰/修行系統

#### 女僕教堂 — 離線打坐掛機 `/meditate_start` `/meditate_stop`

玩家需走到女僕教堂節點後開始打坐。打坐期間無法進行任何動作（含移動、戰鬥、交易）。

| 參數 | 值 |
|------|-----|
| 打坐期間限制 | 不可 `/move`、不可戰鬥、不可交易 |
| 結束方式 | `/meditate_stop` |
| 托幣獎勵 | ~60 托幣/小時 |
| 戰利品 | 隨機掉落（初始草原掉落池，期望值 = 體力刷副本收益 50%） |
| 元神經驗 | 10 EXP/小時 |
| 元神升級 | 每級需 (等級+1)×50 EXP，升級 HP+5、體力上限+5 |
| 轉法輪 | 獨立活動道具，立即獲得元神值（與打坐無關） |

#### 大士爺廟 — 膜拜 `/pray`

大士爺 = 台灣民間信仰的鬼王（面燃大士／普渡公），觀世音菩薩化現。廟內受鬼王神力保護。

| 參數 | 值 |
|------|-----|
| 每日香火 | 3 柱（每日重置） |
| 每次消耗 | 3 柱 |
| 滿血恢復 | ✅ |
| 攻擊 buff | +50%，持續 30 分鐘 |
| 修為進度 | +1/次 |
| 修為升級 | 每級需 (等級+1)×3 次膜拜，升級能力點+1 |
| 限制 | 廟內安全，但需穿過翡翠森林（路途危險） |

## 五、經濟系統參數

### 5.1 貨幣體系

```
簽到拜拜 ──→ 🪙 安幣（活躍幣） ──→ 寶箱、彩券
贊助贊助 ──→ 💵 逸幣（贊助幣） ──→ 恢復體力
活動得獎 ──→ 💶 烏幣（活動幣） ──→ 提升戰力、提升體力
賣戰利品 ──→ 💴 托幣（副本幣） ──→ 提升戰力、買烏龜
尚未安排 ──→ 💷 邦幣（公共財） ──→ 世界建設
```

| 貨幣 | 別名 | 取得方式 | 用途 |
|------|------|---------|------|
| 🪙 安幣 | 活躍幣 | 每日簽到 | 寶箱、彩券 |
| 💵 逸幣 | 贊助幣 | Buy Me a Coffee 儲值 | 恢復體力 |
| 💶 烏幣 | 活動幣 | 競賽活動得獎 | 提升戰力（能力點）、提升體力上限 |
| 💴 托幣 | 副本幣 | 出售戰利品 | 提升戰力（能力點）、購買烏龜股票 |
| 💷 邦幣 | 公共財 | 全服討伐世界魔皇、節慶全服目標 | 世界建設：建造公共建築、提升節點治安、解鎖新區域 |

### 5.2 每日簽到獎勵

| 參數 | 值 |
|------|-----|
| 基礎安幣 | 10 元/天 |
| 連續加成 | +20 元/天 |
| 每日上限 | 250 元 |
| 公式 | `min(10 + (連續天數 − 1) × 20, 250)` |
| 中斷簽到 | 連續天數重置為 1 |
| 安幣用途 | 能力重置（500 安幣/次） |

### 5.3 商店定價策略

#### 戰利品賣價（浮動）- 每 30 分鐘更新

| 機制 | 值 |
|------|-----|
| 波動範圍 | ±15% |
| 價格下限 | base_price × 0.3 |
| 價格上限 | base_price × 3 |
| 趨勢顯示 | 🔺 上漲 / 🔻 下跌 / ➖ 持平 |

#### 消耗品買價（固定）- 預留活動折扣

| 道具 | 價格 | 貨幣 | 效果 |
|------|------|------|------|
| 恢復劑 | 100 | 托幣 | 恢復 50 體力 + 50 HP |
| 強效恢復劑 | 300 | 托幣 | 恢復 150 體力 + 150 HP |
| 線香 | 50 | 托幣 | —（大士爺廟用每日香火，非線香） |
| 糖果 | 30 | 托幣 | 供奉精靈 |
| 轉法輪 | 500 | 托幣 | 立即獲得元神值（活動限定，商店不可購買） |

`items` 表預留 `event_discount` 欄位（可設為 NULL 或折扣百分比）。

### 5.4 體力回復

| 參數 | 值 |
|------|-----|
| 自然回復 | 每分鐘 +1 點（只在玩家在線時生效） |
| 恢復劑 | 瞬間回復 50 點體力 + 50 HP |
| 強效恢復劑 | 瞬間回復 150 點體力 + 150 HP |
| 上限提升 | 可透過道具/任務增加 max_stamina |

## 六、Bot ① 號 — 指令規格（RPG 核心 + 管理 + 社交）

### 6.1 註冊 `/register`
- **權限**：所有人
- **限制**：<#969825727371423755>
- **效果**：建立角色（ATK10/DEF5/HP100, 體150），出生於烏托邦主城

### 6.2 個人檔案 `/profile [user]`
- **限制**：<#968157417789595709>
- 顯示角色完整狀態（含元神等級、修為等級、打坐狀態）

### 6.3 每日簽到 `/daily`
- **限制**：<#969830297032097802>
- 公式：`min(10 + (streak-1)×20, 250)` 安幣

### 6.4 背包 `/bag`
- **限制**：<#968157417789595709>

### 6.5 野區探索 `/explore <zone>`
- **限制**：城外限定 + 戰鬥頻道 <#1508353757161721857>
- 需先 `/move` 出城才可使用

### 6.6 副本挑戰 `/dungeon <boss>`
- **限制**：城外限定 + 戰鬥頻道
- 戰力門檻：低於建議 70% 無法挑戰

### 6.7 世界魔皇 `/world_boss`
- **限制**：城外限定 + 戰鬥頻道
- 獎勵：托幣 + 烏幣

### 6.8 移動 `/move <節點>`
- 依距離計算移動時間（每距離單位 30 秒）
- 移動中不可使用節點相關指令
- 每 15 秒自動檢查是否抵達

### 6.9 移動狀態 `/travel_status`
- 查看當前位置、移動進度、剩餘時間

### 6.10 女僕教堂打坐 `/meditate_start` `/meditate_stop`
- **限制**：<#996338798835286057>
- 離線掛機，結束時領取托幣+戰利品+元神經驗

### 6.11 大士爺廟膜拜 `/pray`
- **限制**：<#996338798835286057>
- 每日 3 柱香，滿血 + 50% ATK buff 30 分 + 修為累積

### 6.12 能力分配 `/ability <stat> <amount>`
- **無頻道限制**

### 6.13 能力重置 `/ability_reset`
- 500 安幣，每週一次

### 5.13 社交互動指令

| 指令 | 功能 |
|------|------|
| `/hug <user>` | 擁抱某人 |
| `/kiss <user>` | 親吻某人 |
| `/pat <user>` | 摸頭 |
| `/slap <user>` | 打巴掌 |
| `/kill <user>` | 假裝殺死 |
| `/wink <user>` | 眨眼 |
| `/gif <type>` | 隨機 GIF (hug/kiss/cuddle/pat/kill/slap/wink) |

### 5.14 工具指令

| 指令 | 功能 | 權限 |
|------|------|------|
| `/divider` | 產生分隔線 | 所有人 |
| `/draw_lots <count> <options...>` | 抽籤 | 所有人 |
| `/dice <big_or_small>` | 猜大小 | 所有人 |
| `/guess_number <number>` | 猜數字 (1~100) | 所有人 |
| `/slot` | 拉霸機 | 所有人 |
| `/rps <choice>` | 剪刀石頭布 | 所有人 |
| `/answer_book <question>` | 解答之書（8-ball 風格） | 所有人 |
| `/yesno <question>` | 是非問答 | 所有人 |
| `/avatar <user>` | 取得頭像 | 所有人 |
| `/ping` | 延遲查詢 | 所有人 |
| `/anon <message>` | 匿名留言（DM 機器人） | 所有人 |
| `/vote_create <title> <options>` | 發起投票 | 所有人 |
| `/iwin` | 直接勝利（梗指令） | 所有人 |
| `/nickname <name>` | 更改伺服器暱稱 | 所有人 |
| `/clean <count>` | 批量刪除訊息 | 管理員 |
| `/dm_me` | 機器人主動私訊 | 所有人 |

## 七、Bot ② 號 — 指令規格（經濟 + 活動）

### 7.1 商店 `/shop [category]`
- 材料顯示浮動賣價、消耗品顯示固定托幣買價

### 7.2 購買 `/shop_buy <item> <quantity>`
- **貨幣**：托幣
- `/shop_price <item>` 查材料賣價

### 7.3 出售 `/shop_sell <item> <quantity>`
- **貨幣**：托幣

### 7.4 托幣彩券 `/lottery_buy` `/lottery_auto`
- 01~20 選 3 碼，可變投注金
- 開 3+1 特別號，頭獎 100x / 貳獎 10x / 叁獎 5x
- 購買時 DM 確認
- `/lottery_check` 兌獎、`/lottery_rules` 規則

### 6.9 股市行情 `/market`
- **顯示**：6 種烏龜股票價格 + 漲跌幅（24hr 對比）

### 6.10 投資買入 `/invest_buy <stock> <quantity>`
- **貨幣**：托幣
- **檢查**：托幣是否足夠

### 6.11 投資賣出 `/invest_sell <stock> <quantity>`
- **收益**：current_price × quantity（托幣）

### 6.12 投資組合 `/invest_portfolio`
- **顯示**：持股清單、成本、現值、損益

### 6.13 寵物抽卡 `/pet_gacha [count]`
- **價格**：500 逸幣/抽
- **機率**：教主 1%、灰啾啾 3.8%、胖柴 3.8%、灰吱吱 3.8%、啾太郎 3.8%（剩餘 = 未中獎）
- **保底**：50 抽必定獲得 rare 以上

### 6.14 寵物列表 `/pet_list`
- **顯示**：所有寵物（名稱、等級、經驗、是否出戰）

### 6.15 寵物出戰 `/pet_equip <pet_name>`
- **切換**：當前出戰寵物

### 6.16 寵物天堂 `/pet_battle`
- **消耗**：體力 5
- **寵物**：選中的 pet 與野生怪物戰鬥，獲得寵物經驗

### 6.17 成就 `/achievements`
- **顯示**：所有成就 + 進度狀態

### 6.18 排行榜 `/rank <category>`
- **category**：power（戰力）/ wealth（安幣總額）/ signin（簽到連續天數）
- **顯示**：前 10 名

### 6.19 你寧可投稿 `/wyr <question> <option_a> <option_b>`
- **儲存**：投稿到資料庫
- **舊語法**：`#would_you_rather` 搬移

### 6.20 活動 `/event`
- **顯示**：當前進行中的活動資訊

## 八、背景排程任務

| 任務 | Bot | 頻率 | 說明 |
|------|-----|------|------|
| 股票價格更新 | ① | 15 分鐘 | 6 種股票隨機波動 |
| 材料賣價更新 | ① | 30 分鐘 | 10 種材料賣價浮動 |
| 體力回復 | ① | 每分鐘 | 在線玩家體力 +1 |
| 簽到重置 | ① | 每日 00:00 UTC+8 | 重置每日簽到限制 |
| 世界魔皇重置 | ① | 每日 00:00 或擊殺後 | 重置 HP 為 600,000 |
| 月卡檢查 | ① | 每日 | 檢查並移除過期月卡 |

## 九、遊戲流程圖

```
新玩家
  │
  ├── /register ──── 建立角色 (ATK10/DEF5/HP100, 體150, 全貨幣0)
  │                   ├── 解鎖成就「初來乍到」
  │
  ├── /daily ─────── 簽到拿安幣 (100 + streak×20, 月卡+逸幣)
  │                   ├── 連續簽到解鎖成就
  │
  ├── /explore ───── 消耗體力打野怪
  │   ├── 草原外圍 (8體) → 黏液/羽毛/肉/羊毛
  │   ├── 草原內部 (10體) → 牙齒/皮革/骨頭 + 罕見怪
  │   ├── 森林外圍 (12體) → 骨頭/毒液/魔石
  │   ├── 森林內部 (15體) → 皮革/魔石/緞帶(極稀有)
  │   └── 沿海小徑 (14體) → 骨頭/魔石/毒液/緞帶
  │
  ├── /shop_sell ─── 賣材料換托幣 (浮動價格, 看時機賣)
  │
  ├── /pray ──────── 膜拜消耗線香獲得修為
  │   └── /meditate ─ 坐禪回復修為
  │
  ├── /ability ───── 分配能力點 (ATK↑ / DEF↑ / HP↑)
  │
  ├── /dungeon ───── 挑戰副本 Boss (需戰力門檻)
  │   ├── 殭屍 (戰力2800) → 骨頭/魔石/線香
  │   ├── 軍團 (戰力24300) → 皮革/魔石/線香
  │   ├── 女僕緞帶 (戰力218700) → 緞帶/魔石/轉法輪
  │   └── 女僕們 (戰力1749600) → 大量稀有獎勵
  │
  ├── /world_boss ── 世界魔皇討伐 (全域共鬥)
  │
  ├── /arena ─────── PvP 競技場
  │
  ├── /shop_buy ──── 用安幣買消耗品 (固定價)
  │   ├── 恢復劑 $100 / 強效恢復劑 $300
  │   ├── 線香 $50 / 糖果 $30
  │   └── 轉法輪 $500
  │
  └── /invest_* ──── 托幣投資股票
      ├── 低買高賣賺差價
      └── 6 種烏龜不同波動率
```

## 十、檔案結構

```
YCAIR-DCBOT/
├── bot1_main.py              # Bot ① 入口
├── bot2_main.py              # Bot ② 入口
├── .venv/                    # Python 虛擬環境
├── note/
│   └── architecture.md       # 本技術規格書
├── src/
│   ├── __init__.py
│   ├── config.py             # 配置（Token、遊戲參數）
│   ├── database.py           # PostgreSQL 資料庫層
│   └── cogs/
│       ├── __init__.py
│       ├── registration.py   # 註冊系統
│       ├── profile.py        # 角色檔案
│       ├── daily.py          # 每日簽到
│       ├── inventory.py      # 背包系統
│       ├── combat.py         # 戰鬥系統（野區/副本/祭壇/世界魔皇）
│       ├── arena.py          # 競技場 PvP
│       ├── faith.py          # 信仰系統（膜拜/坐禪）
│       ├── stats_ability.py  # 能力點分配
│       ├── social.py         # 社交互動（hug/kiss/pat...）
│       ├── utility.py        # 工具指令（抽籤/投票/解答書...）
│       ├── admin.py          # 管理指令（匿名/清理/公告）
│       ├── shop.py           # 商店系統（Bot2）
│       ├── lottery.py        # 彩券系統（Bot2）
│       ├── investment.py     # 投資交易所（Bot2）
│       ├── pet.py            # 寵物系統（Bot2）
│       ├── achievements.py   # 成就系統（Bot2）
│       ├── ranking.py        # 排行榜（Bot2）
│       └── events.py         # 活動系統（Bot2）
```

## 十一、技術棧

| 項目 | 技術 |
|------|------|
| 語言 | Python 3.13 |
| Discord API 函式庫 | discord.py 2.7.1 |
| 資料庫 | PostgreSQL 16 |
| 資料庫驅動 | asyncpg 0.31 |
| 指令系統 | Slash Commands (app_commands) |
| 架構模式 | Cog-based (discord.ext.commands.Cog) |
| 執行時期 | asyncio (async/await) |

## 十二、實作狀態

### ✅ 已完成模組

| 模組 | 檔案 | 指令數 | 頻道限制 |
|------|------|--------|---------|
| 資料庫層 | `src/database.py` | — | — |
| 配置 | `src/config.py` | — | — |
| 頻道守衛 | `src/channel_guard.py` | — | — |
| Bot ① 主程式 | `bot1_main.py` | — | — |
| Bot ② 主程式 | `bot2_main.py` | — | — |
| 註冊系統 | `cogs/registration.py` | `/register` | ✅ register (969825727371423755) |
| 角色檔案 | `cogs/profile.py` | `/profile [user]` | ✅ profile |
| 每日簽到 | `cogs/daily.py` | `/daily` | ✅ daily |
| 背包道具 | `cogs/inventory.py` | `/bag`, `/use` | ✅ bag |
| 商店系統 | `cogs/shop.py` | `/shop`, `/shop_buy`, `/shop_sell` | ✅ shop |
| 戰鬥系統 | `cogs/combat.py` | `/explore`, `/dungeon`, `/altar`, `/world_boss` | ✅ combat/altar/world_boss |
| 信仰系統 | `cogs/faith.py` | `/pray`, `/meditate` | ✅ pray/meditate |
| 能力分配 | `cogs/stats_ability.py` | `/ability` | ✅ profile |
| 社交互動 | `cogs/social.py` | `/hug`, `/kiss`, `/pat`, `/slap`, `/kill`, `/wink` | 無限制 |
| 工具指令 | `cogs/utility.py` | `/draw_lots`, `/dice`, `/guess_number`, `/slot`, `/rps`, `/answer_book`, `/yesno`, `/avatar`, `/ping`, `/iwin`, `/divider`, `/nickname`, `/anon`, `/clean`, `/dm_me`, `/vote_create` | 依個別設定 |
| 彩券系統 | `cogs/lottery.py` | `/lottery_buy`, `/lottery_auto`, `/lottery_vip`, `/lottery_check` | ✅ lottery |
| 投資系統 | `cogs/investment.py` | `/market`, `/invest_buy`, `/invest_sell`, `/invest_portfolio` | ✅ invest |
| 寵物系統 | `cogs/pet.py` | `/pet_gacha`, `/pet_list`, `/pet_equip`, `/pet_battle` | ✅ pet/pet_heaven |
| 成就系統 | `cogs/achievements.py` | `/achievements` | ✅ profile |
| 排行榜 | `cogs/ranking.py` | `/rank` | ✅ profile |
| 活動系統 | `cogs/events.py` | `/wyr`, `/event` | ✅ main_room |

### ⬜ 尚未實作

| 項目 | 優先度 | 說明 |
|------|--------|------|
| 競技場 PvP | 中 | `/arena` 玩家對戰（資料表已有） |
| 世界魔皇全域 HP | 低 | 目前 HP 未全域同步（每玩家獨立討伐） |
| 聊天經驗值累積 | 低 | 監聽非指令訊息自動加 EXP |
| 體力自然回復 | 低 | 定時每分鐘回復在線玩家體力 | ✅ 已實作 |
| 成就自動檢查 | 低 | 完成特定條件時自動解鎖成就 |
| 彩券定時開獎 | 低 | 自動定時抽出開獎號碼 |
| 月卡系統 | 低 | 購買/開通月卡功能 |
| 搗蛋精靈供奉 | 低 | 消耗糖果獲得烏幣 |
| 寶箱系統 | 低 | 寶箱領取 `/chest` |
| 大士爺廟活動 | 低 | 節慶活動 |

### 備註
- Bot ① 號負責所有 RPG 核心 + 管理 + 社交（16 個 Cog，37+ 指令）
- Bot ② 號負責經濟 + 活動（7 個 Cog，20+ 指令）
- Bot ① 的背景任務同時負責兩個 Bot 的價格更新（股票 15min / 賣價 30min）
- 所有頻道限制透過 `channel_guard.py` 的 `require_channel()` 統一管理
- 頻道 ID 集中在 `config.py` 的 `CHANNELS` 字典中，方便批次修改

## 十三、Buy Me a Coffee 逸幣儲值系統（規劃中）

### 13.1 架構

```
玩家 → Buy Me a Coffee 付款（留言寫 Discord ID）
         ↓
BMC → POST https://bmc.your-domain.com/buymecoffee
         ↓
Cloudflare Tunnel → localhost:8765 → Bot ① → 發放逸幣
```

### 13.2 Webhook 接收端

| 檔案 | `src/bmc_webhook.py` |
|------|---------------------|
| 監聽埠 | `localhost:8765` |
| 端點 | `POST /buymecoffee` |
| 驗證 | HMAC-SHA256 簽章（`BMC_WEBHOOK_SECRET` 環境變數） |

### 13.3 BMC Webhook Payload

```json
{
  "supporter_name": "玩家名稱",
  "support_coffees": 3,
  "support_amount": 150,
  "support_message": "@OKI#1234 我要儲值逸幣",
  "support_created_on": "2026-05-25T10:00:00Z"
}
```

### 13.4 Discord ID 比對邏輯

1. 從 `support_message` 提取 `@Name#1234` 或純數字 ID（17~20 位）
2. 在 `users` 表中搜尋 `discord_id` 或模糊比對 `username`
3. 未註冊玩家跳過（提示先 `/register`）

### 13.5 匯率

```
1 TWD = 2 逸幣
```

| 付款金額 | 獲得逸幣 |
|---------|---------|
| $50 | 100 |
| $150 | 300 |
| $300 | 600 |
| $500 | 1,000 |

### 13.6 Cloudflare Tunnel 部署

```bash
# 安裝
brew install cloudflared

# 建立 Tunnel
cloudflared tunnel login
cloudflared tunnel create utopia-bmc

# DNS (Cloudflare Dashboard)
# CNAME: bmc.your-domain.com → <tunnel-id>.cfargotunnel.com

# ~/.cloudflared/config.yml
tunnel: <tunnel-id>
credentials-file: /Users/ycair/.cloudflared/<tunnel-id>.json
ingress:
  - hostname: bmc.your-domain.com
    service: http://localhost:8765
  - service: http_status:404

# 啟動
cloudflared tunnel run utopia-bmc
```

### 13.7 Buy Me a Coffee 設定

| 設定 | 值 |
|------|-----|
| Webhook URL | `https://bmc.your-domain.com/buymecoffee` |
| Secret | 自訂密鑰（設為 `BMC_WEBHOOK_SECRET` 環境變數） |

### 13.8 啟動 Bot（含 Webhook）

```bash
BMC_WEBHOOK_SECRET="你的密鑰" .venv/bin/python bot1_main.py
```

輸出：
```
💵 Buy Me a Coffee webhook listening on http://localhost:8765/buymecoffee
```
