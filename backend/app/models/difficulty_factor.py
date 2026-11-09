"""难度系数配置表模型（difficulty_factor，M1 只建表不计算）。"""

from sqlalchemy import Column, DateTime, Integer, String, text

from app.models.base import Base


class DifficultyFactor(Base):
    __tablename__ = "difficulty_factor"

    code = Column(String(16), primary_key=True)
    name = Column(String(16), nullable=False)
    factor = Column(Integer, nullable=False, default=1, server_default="1")
    updated_at = Column(
        DateTime, nullable=True, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )
