"""AI GM context assembler — 從 DB 組裝 LLM prompt 所需的玩家與世界狀態。

完全功能化：現有 DB 函式就夠用，不需新查詢邏輯。
未來接上 LLM 時，直接 import 此模組即可。
"""
from src.database import get_pool, get_user, get_inventory


async def assemble_gm_context(discord_id: int, channel_name: str = "") -> dict:
    """組裝 AI GM 所需的所有脈絡資訊，回傳 dict 可直接序列化為 prompt。"""
    pool = await get_pool()
    async with pool.acquire() as db:
        user = await get_user(db, discord_id)
        if not user:
            return {"error": "player_not_registered"}

        inventory = await get_inventory(db, discord_id)
        inventory_summary = ", ".join(
            f"{r['emoji']} {r['name']} ×{r['quantity']}"
            for r in inventory
        ) if inventory else "空"

        currencies = (
            f"安幣 {user['an_bi']:,} | 逸幣 {user['yi_bi']:,} | "
            f"烏幣 {user['wu_bi']:,} | 托幣 {user['tuo_bi']:,} | "
            f"邦幣 {user['bang_bi']:,}"
        )

        recent_battles = await db.fetch(
            "SELECT zone, enemy, result, turns, battled_at FROM battle_logs "
            "WHERE user_id=$1 ORDER BY battled_at DESC LIMIT 5",
            str(discord_id),
        )
        battle_summary = "\n".join(
            f"- {r['battled_at']}: {r['result']} vs {r['enemy']} at {r['zone']} ({r['turns']}t)"
            for r in recent_battles
        ) if recent_battles else "尚無戰鬥記錄"

        active_quests = await db.fetch(
            "SELECT q.*, uq.progress FROM user_quests uq "
            "JOIN quests q ON q.id = uq.quest_id "
            "WHERE uq.user_id=$1 AND uq.status='active'",
            str(discord_id),
        )
        quest_summary = "\n".join(
            f"- [{r['status']}] {r['title']}: {r['description']} (進度 {r['progress']}/{r['objective_count']})"
            for r in active_quests
        ) if active_quests else "無進行中任務"

        reputations = await db.fetch(
            "SELECT r.faction, r.value FROM reputation r WHERE r.user_id=$1",
            str(discord_id),
        )
        rep_summary = "\n".join(
            f"- {r['faction']}: {r['value']}"
            for r in reputations
        ) if reputations else "尚無陣營聲望"

        world_state = await db.fetch("SELECT key, value FROM world_state")
        world_summary = "\n".join(
            f"- {r['key']}: {r['value']}" for r in world_state
        ) if world_state else "無全域事件"

    return {
        "player": {
            "discord_id": str(discord_id),
            "username": user["username"],
            "stamina": f"{user['stamina']}/{user['max_stamina']}",
            "stats": f"ATK {user['attack']} / DEF {user['defense']} / HP {user['hp']}",
            "ability_score": str(
                user['attack'] * 100 + user['defense'] * 50 + user['hp'] * 10
            ),
            "level": user["chat_level"],
            "currencies": currencies,
            "inventory": inventory_summary,
            "current_node": user.get("current_node"),
        },
        "world": {
            "channel": channel_name,
            "active_quests": quest_summary,
            "recent_battles": battle_summary,
            "reputation": rep_summary,
            "world_events": world_summary,
        },
    }
