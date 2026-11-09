"""存储策略抽象接口：返回相对路径，禁止绝对路径入库。"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseStorage(ABC):
    @abstractmethod
    def save(self, *, content: bytes, class_id: int, file_hash: str, ext: str) -> str:
        """保存文件并返回相对路径（相对 UPLOAD_DIR）。"""

    @abstractmethod
    def read(self, relative_path: str) -> bytes:
        """读取文件内容。"""

    @abstractmethod
    def delete(self, relative_path: str) -> None:
        """删除文件；文件不存在视为成功（幂等）。"""

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        """判断文件是否存在。"""

    @abstractmethod
    def abspath(self, relative_path: str) -> str:
        """返回解析后的绝对路径；必须做目录穿越校验。"""
