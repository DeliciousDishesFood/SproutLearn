"""防刷与封顶配置表模型（xp_limit_config，M1 只建表不计算）。"""

from sqlalchemy import Column, DateTime, Integer, String, text

from app.models.base import Base


class XpLimitConfig(Base):
    __tablename__ = "xp_limit_config"

    code = Column(String(32), primary_key=True)
    value = Column(Integer, nullable=False, default=0, server_default="0")
    unit = Column(String(16), nullable=False)
    remark = Column(String(100), nullable=True)
    updated_at = Column(
        DateTime, nullable=True, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )
