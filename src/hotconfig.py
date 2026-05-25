"""Hot-reloadable configuration manager.

Reads from JSON file. Checks file mtime on every attribute access.
If the file changed on disk, reloads automatically — no restart needed.
Thread-safe via asyncio lock.
"""
import asyncio
import json
import os
from pathlib import Path

SETTINGS_PATH = Path(__file__).parent.parent / "settings.json"
_lock = asyncio.Lock()
_cached: dict = {}
_mtime: float = 0


async def _load() -> dict:
    global _cached, _mtime
    try:
        stat = os.stat(SETTINGS_PATH)
        if stat.st_mtime == _mtime and _cached:
            return _cached
        raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        _cached = raw
        _mtime = stat.st_mtime
    except (FileNotFoundError, json.JSONDecodeError) as e:
        if not _cached:
            raise RuntimeError(f"Cannot load settings.json: {e}") from e
    return _cached


async def _refresh():
    async with _lock:
        return await _load()


def _resolve(data: dict, dotted_key: str, default=None):
    keys = dotted_key.split(".")
    for k in keys:
        if isinstance(data, dict) and k in data:
            data = data[k]
        else:
            return default
    return data


class HotConfig:
    """Lazy, auto-reloading config proxy.

    Usage:
        channels = HotConfig("channels")
        sid = await channels.register        # reads settings.json → channels.register

        combat = HotConfig("combat_zones")
        zone = await combat.initial_grassland_outer  # reads combat_zones.initial_grassland_outer
    """

    def __init__(self, prefix: str = ""):
        self._prefix = prefix

    async def _get(self, key: str, default=None):
        data = await _refresh()
        full = f"{self._prefix}.{key}" if self._prefix else key
        return _resolve(data, full, default)

    async def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        return await self._get(name)

    async def get(self, key: str, default=None):
        return await self._get(key, default)

    async def all(self):
        data = await _refresh()
        if self._prefix:
            return _resolve(data, self._prefix, {})
        return data


async def get_channel(cmd_name: str) -> int:
    """Get channel ID for a command. 0 = unrestricted."""
    data = await _refresh()
    return _resolve(data, f"channel_map.{cmd_name}", 0)


async def get_channels() -> dict:
    data = await _refresh()
    return data.get("channels", {})


# Convenience: pre-bound proxies
channels = HotConfig("channels")
channel_map = HotConfig("channel_map")
combat_zones = HotConfig("combat_zones")
dungeon_bosses = HotConfig("dungeon_bosses")
world_boss = HotConfig("world_boss")
game_params = HotConfig("game_params")
