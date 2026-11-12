"""M3.2 金句代理：Redis 缓存 + shiora → hitokoto → 本地池三级兜底。"""

from __future__ import annotations

import json
import random
from typing import Any

import httpx
from loguru import logger

from app.redis_client import get_redis_client
from app.utils.cache_keys import quote_key

LOCAL_QUOTES: list[dict[str, str]] = [
    {"text": "不积跬步，无以至千里。", "from": "荀子"},
    {"text": "知之者不如好之者，好之者不如乐之者。", "from": "孔子"},
    {"text": "路漫漫其修远兮，吾将上下而求索。", "from": "屈原"},
    {"text": "业精于勤，荒于嬉；行成于思，毁于随。", "from": "韩愈"},
    {"text": "纸上得来终觉浅，绝知此事要躬行。", "from": "陆游"},
    {"text": "学而不思则罔，思而不学则殆。", "from": "孔子"},
    {"text": "黑发不知勤学早，白首方悔读书迟。", "from": "颜真卿"},
    {"text": "千淘万漉虽辛苦，吹尽狂沙始到金。", "from": "刘禹锡"},
    {"text": "长风破浪会有时，直挂云帆济沧海。", "from": "李白"},
    {"text": "会当凌绝顶，一览众山小。", "from": "杜甫"},
    {"text": "天行健，君子以自强不息。", "from": "《周易》"},
    {"text": "博观而约取，厚积而薄发。", "from": "苏轼"},
    {"text": "问渠那得清如许？为有源头活水来。", "from": "朱熹"},
    {"text": "读书破万卷，下笔如有神。", "from": "杜甫"},
    {"text": "宝剑锋从磨砺出，梅花香自苦寒来。", "from": "《警世贤文》"},
    {"text": "锲而不舍，金石可镂。", "from": "荀子"},
    {"text": "三人行，必有我师焉。", "from": "孔子"},
    {"text": "海内存知己，天涯若比邻。", "from": "王勃"},
    {"text": "山重水复疑无路，柳暗花明又一村。", "from": "陆游"},
    {"text": "少年易老学难成，一寸光阴不可轻。", "from": "朱熹"},
]


def _cache_get(key: str) -> dict[str, Any] | None:
    try:
        raw = get_redis_client().get(key)
        return json.loads(raw) if raw else None
    except Exception:  # noqa: BLE001 - 缓存失败不阻塞
        return None


def _cache_set(key: str, value: dict[str, Any]) -> None:
    try:
        get_redis_client().setex(key, 600, json.dumps(value, ensure_ascii=False))
    except Exception:  # noqa: BLE001
        pass


def _from_shiora(quote_type: str | None) -> dict[str, Any] | None:
    params = {"type": quote_type} if quote_type else None
    try:
        response = httpx.get("https://quote.shiora.cc/api/quote", params=params, timeout=3)
        if response.status_code != 200:
            return None
        data = response.json()
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            data = data["data"]
        if not isinstance(data, dict):
            return None
        text = data.get("text") or data.get("content") or data.get("quote")
        source = data.get("from") or data.get("source") or "shiora"
        return {"text": str(text), "from": str(source), "source": "shiora"} if text else None
    except Exception:  # noqa: BLE001
        return None


def _from_hitokoto(quote_type: str | None) -> dict[str, Any] | None:
    params = {"c": quote_type} if quote_type else None
    try:
        response = httpx.get("https://v1.hitokoto.cn/", params=params, timeout=3)
        if response.status_code != 200:
            return None
        data = response.json()
        if not isinstance(data, dict) or not data.get("hitokoto"):
            return None
        return {
            "text": str(data["hitokoto"]),
            "from": str(data.get("from_who") or data.get("from") or "hitokoto"),
            "source": "hitokoto",
        }
    except Exception:  # noqa: BLE001
        return None


def get_random_quote(quote_type: str | None = None) -> dict[str, Any]:
    normalized = (quote_type or "all").strip()[:32] or "all"
    key = quote_key(normalized)
    cached = _cache_get(key)
    if cached:
        return cached
    quote = _from_shiora(quote_type) or _from_hitokoto(quote_type)
    if quote is None:
        local = random.choice(LOCAL_QUOTES)
        quote = {**local, "source": "local"}
        logger.info("quote fallback local")
    _cache_set(key, quote)
    return quote
