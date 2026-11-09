"""等级头衔配置表模型（level_def，M1 只建表不计算）。"""

from sqlalchemy import Column, Integer, String

from app.models.base import Base, tinyint_unsigned


class LevelDef(Base):
    __tablename__ = "level_def"

    level = Column(tinyint_unsigned(), primary_key=True)
    title = Column(String(20), nullable=False)
    min_xp = Column(Integer, nullable=False, default=0, server_default="0")
