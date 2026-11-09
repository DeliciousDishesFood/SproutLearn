"""存储策略工厂：生产使用 LocalStorage，测试可注入内存/临时目录实现。"""

from __future__ import annotations

from app.config import get_settings
from app.strategies.storage.base import BaseStorage
from app.strategies.storage.local_storage import LocalStorage

_storage: BaseStorage | None = None


def get_storage() -> BaseStorage:
    global _storage
    if _storage is None:
        _storage = LocalStorage(get_settings().upload_dir)
    return _storage


def set_storage(storage: BaseStorage | None) -> None:
    """测试注入或应用关闭时重置。"""
    global _storage
    _storage = storage


__all__ = ["BaseStorage", "LocalStorage", "get_storage", "set_storage"]
