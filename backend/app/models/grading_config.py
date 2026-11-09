"""判分配置表模型（grading_config，M2 使用；M1 仅建表）。"""

from sqlalchemy import Column, DateTime, String, text

from app.models.base import Base


class GradingConfig(Base):
    __tablename__ = "grading_config"

    code = Column(String(32), primary_key=True)
    value = Column(String(64), nullable=False)
    remark = Column(String(100), nullable=True)
    updated_at = Column(
        DateTime, nullable=True, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )
