"""Buy Me a Coffee webhook receiver.

Cloudflare Tunnel exposes this to a public URL.
Buy Me a Coffee sends POST requests with payment info.
Bot grants 逸幣 based on the amount and Discord ID in the message.
"""
import json
import re
import hashlib
import hmac
from aiohttp import web

from src.database import get_pool

# TWD → 逸幣 conversion rate
EXCHANGE_RATE = 2  # 1 TWD = 2 逸幣


def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    if not secret:
        return True
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def handle_bmc(request: web.Request):
    body = await request.read()
    sig = request.headers.get("X-BMC-Signature", "")
    secret = request.app.get("bmc_secret", "")

    if not verify_signature(body, sig, secret):
        return web.Response(status=403, text="Invalid signature")

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return web.Response(status=400, text="Invalid JSON")

    supporter = data.get("supporter_name", "Unknown")
    amount_twd = data.get("support_amount", 0)
    message = data.get("support_message", "")
    coffees = data.get("support_coffees", 0)

    discord_id = None
    mention_match = re.search(r"@(\S+#\d{4})", message)
    id_match = re.search(r"(\d{17,20})", message)
    if id_match:
        discord_id = id_match.group(1)
    elif mention_match:
        discord_id = mention_match.group(1)

    if not discord_id:
        return web.Response(status=200, text="No Discord ID found in message")

    yi_bi = amount_twd * EXCHANGE_RATE

    pool = await get_pool()
    async with pool.acquire() as db:
        user = await db.fetchrow(
            "SELECT discord_id, username FROM users WHERE discord_id=$1", discord_id,
        )
        if not user:
            mention_name = mention_match.group(1) if mention_match else None
            if mention_name:
                user = await db.fetchrow(
                    "SELECT discord_id, username FROM users WHERE username ILIKE $1",
                    f"%{mention_match.group(1).split('#')[0]}%",
                )
        if not user:
            return web.Response(status=200, text=f"User {discord_id} not registered yet")

        await db.execute(
            "UPDATE users SET yi_bi=yi_bi+$1 WHERE discord_id=$2",
            yi_bi, user["discord_id"],
        )

    print(f"💵 BMC: {supporter} paid {amount_twd} TWD → +{yi_bi} 逸幣 → {user['username']}")
    return web.Response(status=200, text=f"OK: +{yi_bi} 逸幣 for {user['username']}")


def create_bmc_app(secret: str = "") -> web.Application:
    app = web.Application()
    app["bmc_secret"] = secret
    app.router.add_post("/buymecoffee", handle_bmc)
    return app
