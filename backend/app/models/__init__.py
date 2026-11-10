"""模型包：统一导入，保证 Base.metadata 包含 M1 13 表 + M2A 判分结果表。"""

from app.models.base import Base
from app.models.class_ import Class
from app.models.class_invite import ClassInvite
from app.models.difficulty_factor import DifficultyFactor
from app.models.grading_config import GradingConfig
from app.models.grading_result import GradingResult
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_doc import KnowledgeDoc
from app.models.level_def import LevelDef
from app.models.login_streak_rule import LoginStreakRule
from app.models.qq_binding import QqBinding
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.xp_config import XpConfig
from app.models.xp_limit_config import XpLimitConfig

__all__ = [
    "Base",
    "Teacher",
    "Class",
    "ClassInvite",
    "Student",
    "QqBinding",
    "XpConfig",
    "DifficultyFactor",
    "LoginStreakRule",
    "XpLimitConfig",
    "LevelDef",
    "GradingConfig",
    "GradingResult",
    "KnowledgeDoc",
    "KnowledgeChunk",
]
