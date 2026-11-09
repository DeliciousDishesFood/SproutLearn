"""行为经验配置表模型（xp_config，M1 只建表不计算）。"""

from sqlalchemy import Column, DateTime, Integer, String, text

from app.models.base import Base, tinyint


class XpConfig(Base):
    __tablename__ = "xp_config"

    code = Column(String(32), primary_key=True)
    name = Column(String(50), nullable=False)
    base_xp = Column(Integer, nullable=False, default=0, server_default="0")
    enabled = Column(tinyint(), nullable=False, default=1, server_default="1")
    updated_at = Column(
        DateTime, nullable=True, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )
