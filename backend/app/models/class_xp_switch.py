"""M3.2 班级经验开关（class_xp_switch）。"""

from sqlalchemy import Column, ForeignKey, String

from app.models.base import Base, bigint_unsigned, tinyint


class ClassXpSwitch(Base):
    __tablename__ = "class_xp_switch"

    class_id = Column(
        bigint_unsigned(),
        ForeignKey("class.id", ondelete="CASCADE"),
        primary_key=True,
    )
    code = Column(String(32), primary_key=True)
    enabled = Column(tinyint(), nullable=False, default=1, server_default="1")
