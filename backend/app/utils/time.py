"""时间工具：统一 Asia/Shanghai 与契约时间字符串格式。"""

from datetime import datetime, timezone

from app.config import get_settings


def now() -> datetime:
    """返回配置时区的当前时间（带 tzinfo）。"""
    return datetime.now(get_settings().timezone)


def now_naive() -> datetime:
    """返回配置时区的本地 naive 时间，用于与 MySQL DATETIME 比较。"""
    return now().replace(tzinfo=None)


def now_str() -> str:
    """返回契约要求的 `YYYY-MM-DD HH:mm:ss` 字符串。"""
    settings = get_settings()
    return now().astimezone(settings.timezone).strftime(settings.datetime_format)


def fmt_dt(value: datetime | None) -> str | None:
    """把数据库时间格式化为契约时间字符串；None 原样返回。"""
    if value is None:
        return None
    settings = get_settings()
    if value.tzinfo is None:
        value = value.replace(tzinfo=settings.timezone)
    return value.astimezone(settings.timezone).strftime(settings.datetime_format)


def to_epoch(value: datetime | None) -> int | None:
    """datetime → Unix 秒；用于 JWT 与 Redis TTL 计算。"""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=get_settings().timezone)
    return int(value.timestamp())


def utc_now_epoch() -> int:
    """当前 UTC 时间戳（JWT iat/exp 使用）。"""
    return int(datetime.now(timezone.utc).timestamp())
