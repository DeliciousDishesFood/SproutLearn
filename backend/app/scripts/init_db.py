"""建表入口（开发辅助）：直接按模型创建 13 张表。

生产/首次部署请使用 Alembic：`alembic upgrade head`。
"""

from __future__ import annotations

from loguru import logger

from app.database import engine
from app.models import Base


def main() -> None:
    logger.info("按 SQLAlchemy 模型创建表（开发辅助）")
    Base.metadata.create_all(bind=engine)
    logger.info("建表完成：{}", ", ".join(sorted(Base.metadata.tables.keys())))


if __name__ == "__main__":
    main()
