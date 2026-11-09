"""本地磁盘存储实现：命名规则 {class_id}/{sha256[:2]}/{sha256}{ext}。"""

from __future__ import annotations

import os
import re
from pathlib import Path

from loguru import logger

from app.strategies.storage.base import BaseStorage

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class LocalStorage(BaseStorage):
    def __init__(self, root: str) -> None:
        self.root = os.path.realpath(os.path.expanduser(root))
        Path(self.root).mkdir(parents=True, exist_ok=True)
        if not os.access(self.root, os.W_OK):
            raise RuntimeError(f"上传目录不可写: {self.root}")

    def _abs(self, relative_path: str) -> str:
        """防止 ../ 目录穿越；任何越界路径直接拒绝。"""
        candidate = os.path.realpath(os.path.join(self.root, relative_path))
        if candidate != self.root and not candidate.startswith(self.root + os.sep):
            raise ValueError("路径越界")
        return candidate

    def save(self, *, content: bytes, class_id: int, file_hash: str, ext: str) -> str:
        if not _HASH_RE.match(file_hash or ""):
            raise ValueError("file_hash 非法")
        if not isinstance(class_id, int) or class_id <= 0:
            raise ValueError("class_id 非法")
        suffix = f".{ext.lower().lstrip('.')}" if ext else ""
        relative_path = f"{class_id}/{file_hash[:2]}/{file_hash}{suffix}"
        target = self._abs(relative_path)
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        if os.path.exists(target):
            return relative_path
        temp_path = f"{target}.tmp"
        with open(temp_path, "wb") as handle:
            handle.write(content)
        os.replace(temp_path, target)
        return relative_path

    def read(self, relative_path: str) -> bytes:
        with open(self._abs(relative_path), "rb") as handle:
            return handle.read()

    def delete(self, relative_path: str) -> None:
        try:
            os.remove(self._abs(relative_path))
        except FileNotFoundError:
            return
        except OSError as exc:  # noqa: BLE001 - 删除失败只记日志
            logger.warning("删除上传文件失败 {}: {}", relative_path, exc)

    def exists(self, relative_path: str) -> bool:
        return os.path.isfile(self._abs(relative_path))

    def abspath(self, relative_path: str) -> str:
        return self._abs(relative_path)
