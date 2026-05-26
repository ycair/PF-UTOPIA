"""推薦系統：Hashids 無狀態編碼 + 延遲派發防弊"""
from hashids import Hashids

SALT = "pf-utopia-referral-2026"
_MIN_LENGTH = 6

_hashids = Hashids(salt=SALT, min_length=_MIN_LENGTH)


def encode_referral(discord_id: int) -> str:
    return _hashids.encode(discord_id)


def decode_referral(code: str) -> int | None:
    try:
        result = _hashids.decode(code)
        return result[0] if result else None
    except (ValueError, IndexError):
        return None
