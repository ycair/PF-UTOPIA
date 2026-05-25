"""AI GM 工具定義與執行器。

工具的「定義」是給 LLM 看的 OpenAI function calling 格式。
工具的「執行」是真實操作 DB / 觸發遊戲機制的 async 函式。

兩者分離：換 LLM provider 時只需改定義格式，執行邏輯不變。
"""
from src.database import get_pool


GM_TOOLS = [
    {
        "name": "give_item",
        "description": "給予玩家道具。物品名稱必須是遊戲中存在的道具。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "玩家的 Discord ID"},
                "item_name": {"type": "string", "description": "道具名稱（必須存在於 items 表）"},
                "quantity": {"type": "integer", "description": "數量"},
            },
            "required": ["user_id", "item_name", "quantity"],
        },
    },
    {
        "name": "modify_currency",
        "description": "增減玩家貨幣。正值增加，負值扣除。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "currency": {
                    "type": "string",
                    "enum": ["an_bi", "yi_bi", "wu_bi", "tuo_bi", "bang_bi"],
                },
                "amount": {"type": "integer"},
            },
            "required": ["user_id", "currency", "amount"],
        },
    },
    {
        "name": "spawn_enemy",
        "description": "在玩家所在位置生成敵人。用於觸發隨機戰鬥。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "enemy_name": {"type": "string"},
                "enemy_hp": {"type": "integer"},
                "enemy_atk": {"type": "integer"},
                "enemy_def": {"type": "integer"},
                "drops": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": [
                            {"type": "string"},
                            {"type": "integer"},
                            {"type": "integer"},
                            {"type": "number"},
                        ],
                    },
                    "description": "掉落物 [[name, qty_min, qty_max, chance], ...]",
                },
                "narrative": {"type": "string", "description": "開場敘述"},
            },
            "required": ["user_id", "enemy_name", "enemy_hp", "enemy_atk", "enemy_def"],
        },
    },
    {
        "name": "start_quest",
        "description": "給予玩家新任務。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "objective_count": {"type": "integer"},
                "reward_an_bi": {"type": "integer"},
                "reward_items": {
                    "type": "object",
                    "description": "{item_name: quantity}",
                },
            },
            "required": ["user_id", "title", "description", "objective_count"],
        },
    },
    {
        "name": "modify_reputation",
        "description": "修改玩家對特定陣營的聲望值。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "faction": {"type": "string"},
                "delta": {"type": "integer", "description": "正=增加，負=減少"},
            },
            "required": ["user_id", "faction", "delta"],
        },
    },
    {
        "name": "set_world_state",
        "description": "設定全域世界狀態變數。例如天氣、節日、戰爭狀態。",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "value": {"type": "string"},
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "send_narrative",
        "description": "發送純敘事文字（不觸發任何遊戲機制）。用於角色扮演對話。",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
            },
            "required": ["text"],
        },
    },
]


async def execute_tool(tool_name: str, arguments: dict) -> dict:
    """執行一個 GM 工具呼叫，回傳結果 dict。"""
    pool = await get_pool()
    async with pool.acquire() as db:
        match tool_name:

            case "give_item":
                item = await db.fetchrow(
                    "SELECT id FROM items WHERE name=$1", arguments["item_name"]
                )
                if not item:
                    return {"error": f"未知道具: {arguments['item_name']}"}
                await db.execute(
                    "INSERT INTO inventory (user_id, item_id, quantity) VALUES ($1,$2,$3) "
                    "ON CONFLICT (user_id, item_id) DO UPDATE SET quantity=inventory.quantity+$3",
                    arguments["user_id"], item["id"], arguments["quantity"],
                )
                return {
                    "ok": True,
                    "detail": f"給予 {arguments['item_name']} ×{arguments['quantity']}",
                }

            case "modify_currency":
                currency = arguments["currency"]
                await db.execute(
                    f"UPDATE users SET {currency}={currency}+$1 WHERE discord_id=$2",
                    arguments["amount"], arguments["user_id"],
                )
                return {
                    "ok": True,
                    "detail": f"{currency} {'+' if arguments['amount'] >= 0 else ''}{arguments['amount']}",
                }

            case "spawn_enemy":
                drops = arguments.get("drops", [])
                return {
                    "ok": True,
                    "enemy": {
                        "name": arguments["enemy_name"],
                        "hp": arguments["enemy_hp"],
                        "atk": arguments["enemy_atk"],
                        "def": arguments["enemy_def"],
                        "drops": drops,
                    },
                    "narrative": arguments.get("narrative", ""),
                }

            case "start_quest":
                await db.execute(
                    "INSERT INTO quests (title, description, objective_count, reward_an_bi, reward_items) "
                    "VALUES ($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING",
                    arguments["title"],
                    arguments["description"],
                    arguments["objective_count"],
                    arguments.get("reward_an_bi", 0),
                    arguments.get("reward_items", {}),
                )
                quest = await db.fetchrow(
                    "SELECT id FROM quests WHERE title=$1", arguments["title"]
                )
                if quest:
                    await db.execute(
                        "INSERT INTO user_quests (user_id, quest_id, status) VALUES ($1,$2,'active') "
                        "ON CONFLICT DO NOTHING",
                        arguments["user_id"], quest["id"],
                    )
                return {"ok": True, "detail": f"任務已發放: {arguments['title']}"}

            case "modify_reputation":
                await db.execute(
                    "INSERT INTO reputation (user_id, faction, value) VALUES ($1,$2,$3) "
                    "ON CONFLICT (user_id, faction) DO UPDATE SET value=reputation.value+$3",
                    arguments["user_id"], arguments["faction"], arguments["delta"],
                )
                return {
                    "ok": True,
                    "detail": f"{arguments['faction']} 聲望 {'+' if arguments['delta'] >= 0 else ''}{arguments['delta']}",
                }

            case "set_world_state":
                await db.execute(
                    "INSERT INTO world_state (key, value) VALUES ($1,$2) "
                    "ON CONFLICT (key) DO UPDATE SET value=$2",
                    arguments["key"], arguments["value"],
                )
                return {"ok": True, "detail": f"全域狀態 {arguments['key']} = {arguments['value']}"}

            case "send_narrative":
                return {"ok": True, "text": arguments["text"]}

            case _:
                return {"error": f"未知工具: {tool_name}"}
