"""loguru 日志配置：控制台输出、request_id 注入、级别来自 LOG_LEVEL。"""

from __future__ import annotations

import logging
import sys

from loguru import logger

from app.config import get_settings
from app.utils.response import get_request_id


class _InterceptHandler(logging.Handler):
    """把标准 logging（uvicorn/sqlalchemy）转发到 loguru。"""

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - 框架适配
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


def _patcher(record: dict) -> None:
    record["extra"].setdefault("request_id", get_request_id() or "-")


def setup_logging() -> None:
    """应用启动时调用一次。"""
    settings = get_settings()
    logger.remove()
    logger.configure(patcher=_patcher)
    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
            "rid=<cyan>{extra[request_id]}</cyan> | <level>{message}</level>"
        ),
        enqueue=False,
        backtrace=False,
        diagnose=False,
    )
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(name).handlers = [_InterceptHandler()]
        logging.getLogger(name).propagate = False
