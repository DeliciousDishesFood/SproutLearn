"""M3.2 学生每日经验快照（student_daily_xp）。"""

from sqlalchemy import Column, Date, ForeignKey, Integer, UniqueConstraint

from app.models.base import Base, bigint_unsigned, pk_bigint, tinyint


class StudentDailyXp(Base):
    __tablename__ = "student_daily_xp"
    __table_args__ = (
        UniqueConstraint("student_id", "stat_date", name="uk_daily_student_date"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    student_id = Column(
        bigint_unsigned(), ForeignKey("student.id", ondelete="CASCADE"), nullable=False
    )
    stat_date = Column(Date, nullable=False)
    login_xp = Column(Integer, nullable=False, default=0, server_default="0")
    practice_xp = Column(Integer, nullable=False, default=0, server_default="0")
    streak_xp = Column(Integer, nullable=False, default=0, server_default="0")
    submission_xp = Column(Integer, nullable=False, default=0, server_default="0")
    total_xp = Column(Integer, nullable=False, default=0, server_default="0")
    login_awarded = Column(tinyint(), nullable=False, default=0, server_default="0")
