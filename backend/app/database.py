"""SQLAlchemy Engine / SessionLocal / get_db；所有仓储共享同一会话工厂。"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,
    pool_size=_settings.mysql_pool_size,
    max_overflow=_settings.mysql_pool_max_overflow,
    connect_args={"connect_timeout": 2},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：每个请求一个 Session，请求结束关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
