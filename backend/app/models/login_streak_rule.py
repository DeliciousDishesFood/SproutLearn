"""连续登录规则表模型（login_streak_rule，M1 只建表不计算）。"""

from sqlalchemy import Column, Integer

from app.models.base import Base, tinyint_unsigned


class LoginStreakRule(Base):
    __tablename__ = "login_streak_rule"

    streak_day = Column(tinyint_unsigned(), primary_key=True)
    xp = Column(Integer, nullable=False, default=0, server_default="0")
