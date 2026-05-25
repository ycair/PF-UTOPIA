import asyncio, os, sys, secrets, time
from aiohttp import web

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
DISCORD_API = "https://discord.com/api/v10"
CLIENT_ID = "921779959717048340"
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "https://utopia.ycair.space/callback.html")
JWT_TOKENS = {}

import aiohttp as aiohttp_client


async def auth_callback(request: web.Request):
    code = request.query.get("code")
    if not code: return web.json_response({"error":"missing code"}, status=400)
    async with aiohttp_client.ClientSession() as s:
        data = {"client_id":CLIENT_ID,"client_secret":CLIENT_SECRET,"grant_type":"authorization_code","code":code,"redirect_uri":REDIRECT_URI}
        async with s.post(f"{DISCORD_API}/oauth2/token", data=data, headers={"Content-Type":"application/x-www-form-urlencoded"}) as r:
            if r.status!=200: return web.json_response({"error":"oauth failed"}, status=400)
            td = await r.json()
        headers = {"Authorization":f"Bearer {td['access_token']}"}
        async with s.get(f"{DISCORD_API}/users/@me", headers=headers) as r:
            if r.status!=200: return web.json_response({"error":"user lookup failed"}, status=400)
            ud = await r.json()
    jwt = secrets.token_hex(32)
    JWT_TOKENS[jwt] = {"discord_id":ud["id"],"username":ud["username"],"expires":time.time()+86400*7}
    return web.json_response({"token":jwt,"username":ud["username"]})


def get_user(request: web.Request):
    auth = request.headers.get("Authorization","")
    if not auth.startswith("Bearer "): return None
    data = JWT_TOKENS.get(auth[7:])
    if not data or data["expires"]<time.time(): return None
    return data


async def api_me(request: web.Request):
    u = get_user(request)
    if not u: return web.json_response({"error":"unauthorized"}, status=401)
    from src.database import get_pool
    pool = await get_pool()
    async with pool.acquire() as db:
        row = await db.fetchrow("SELECT * FROM users WHERE discord_id=$1", u["discord_id"])
        if not row: return web.json_response({"error":"not registered"}, status=404)
        row = dict(row)
        nid = row.get("current_node")
        node_name = None
        if nid:
            n = await db.fetchrow("SELECT name FROM map_nodes WHERE id=$1", nid)
            node_name = n["name"] if n else None
        nodes = await db.fetch("SELECT name FROM map_nodes")
        return web.json_response({
            "username":row["username"],"attack":row["attack"],"defense":row["defense"],
            "hp":row["hp"],"current_hp":row.get("current_hp")or row["hp"],
            "stamina":row["stamina"],"max_stamina":row["max_stamina"],
            "an_bi":row["an_bi"],"yi_bi":row["yi_bi"],"wu_bi":row["wu_bi"],
            "tuo_bi":row["tuo_bi"],"bang_bi":row["bang_bi"],
            "current_node_name":node_name,"unlocked_nodes":[n["name"] for n in nodes],
            "chat_level":row["chat_level"],"yuan_shen_level":row.get("yuan_shen_level",0),
            "xiu_wei_level":row.get("xiu_wei_level",0),
        })


async def api_stocks(request: web.Request):
    from src.database import get_pool
    pool = await get_pool()
    async with pool.acquire() as db:
        stocks = await db.fetch("SELECT * FROM stocks ORDER BY id")
        result = []
        for s in stocks:
            s = dict(s)
            prev = await db.fetchval("SELECT price FROM stock_history WHERE stock_id=$1 ORDER BY recorded_at DESC LIMIT 1 OFFSET 1", s["id"])
            prev = prev or s["current_price"]
            change = round((s["current_price"]-prev)/prev*100,1)
            result.append({"name":s["name"],"emoji":s["emoji"],"current_price":s["current_price"],"change":change})
        return web.json_response(result)


async def api_shop_prices(request: web.Request):
    from src.database import get_pool
    pool = await get_pool()
    async with pool.acquire() as db:
        prices = await db.fetch("SELECT i.name,i.emoji,sp.current_price as price FROM shop_sell_prices sp JOIN items i ON i.id=sp.item_id ORDER BY i.id")
        return web.json_response([{"name":p["name"],"emoji":p["emoji"],"price":p["price"]} for p in prices])


async def rankings(request: web.Request, cat: str):
    from src.database import get_pool
    pool = await get_pool()
    async with pool.acquire() as db:
        if cat=="power":
            rows = await db.fetch("SELECT username,(attack*100+defense*50+hp*10) as score FROM users ORDER BY score DESC LIMIT 10")
            return web.json_response([{"username":r["username"],"score":r["score"]} for r in rows])
        else:
            rows = await db.fetch("SELECT username,an_bi FROM users ORDER BY an_bi DESC LIMIT 10")
            return web.json_response([{"username":r["username"],"an_bi":r["an_bi"]} for r in rows])


def create_web_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", lambda r: web.FileResponse(os.path.join(WEB_DIR, "index.html")))
    app.router.add_get("/api/auth/callback", auth_callback)
    app.router.add_get("/api/me", api_me)
    app.router.add_get("/api/stocks", api_stocks)
    app.router.add_get("/api/shop/prices", api_shop_prices)
    app.router.add_get("/api/rankings/power", lambda r: rankings(r,"power"))
    app.router.add_get("/api/rankings/wealth", lambda r: rankings(r,"wealth"))
    app.router.add_static("/", path=WEB_DIR, show_index=False)
    return app


async def main():
    app = create_web_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 8080)
    await site.start()
    print("🌐 Web: http://localhost:8080")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
