import asyncio
from aiohttp import web
import os

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


async def index_handler(request: web.Request):
    return web.FileResponse(os.path.join(WEB_DIR, "index.html"))


def create_web_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", index_handler)
    app.router.add_static("/", path=WEB_DIR, show_index=False)
    return app


async def main():
    app = create_web_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 8080)
    await site.start()
    print("🌐 Web server: http://localhost:8080")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
