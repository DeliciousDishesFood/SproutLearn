"""SQLAlchemy 声明基类与跨方言类型工具。

MySQL 使用无符号大整数 / TINYINT / MEDIUMTEXT；SQLite 测试环境自动降级为
BigInteger / SmallInteger / Text，保证 pytest 无需外部数据库即可跑通。
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Column, DateTime, Integer, SmallInteger, Text, func, text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有模型共享的声明基类。"""


def pk_bigint():
    """主键：MySQL BIGINT UNSIGNED AUTO_INCREMENT；SQLite INTEGER 保证自增。"""
    return BigInteger().with_variant(Integer, "sqlite").with_variant(mysql.BIGINT(unsigned=True), "mysql")


def bigint_unsigned():
    """外键/普通大整数：MySQL 无符号；其他方言普通 BIGINT。"""
    return BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")


def int_unsigned():
    """普通无符号 INT（xp_total）。"""
    return Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")


def tinyint_unsigned():
    return SmallInteger().with_variant(mysql.TINYINT(unsigned=True), "mysql")


def smallint_unsigned():
    return SmallInteger().with_variant(mysql.SMALLINT(unsigned=True), "mysql")


def tinyint():
    return SmallInteger().with_variant(mysql.TINYINT(), "mysql")


def medium_text():
    return Text().with_variant(mysql.MEDIUMTEXT(), "mysql")


class TimestampMixin:
    """业务表公共时间戳：created_at 必填，updated_at 由 DB/ORM 维护。"""

    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.now(),
    )
