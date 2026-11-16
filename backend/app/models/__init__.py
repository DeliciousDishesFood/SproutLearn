"""模型包：统一导入，保证 Base.metadata 包含 M1/M2/M3 全部业务表。"""

from app.models.answer_record import AnswerRecord
from app.models.attempt import Attempt
from app.models.base import Base
from app.models.bot_notice import BotNotice
from app.models.class_ import Class
from app.models.class_bot_config import ClassBotConfig
from app.models.class_invite import ClassInvite
from app.models.class_xp_switch import ClassXpSwitch
from app.models.difficulty_factor import DifficultyFactor
from app.models.grading_config import GradingConfig
from app.models.grading_result import GradingResult
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_doc import KnowledgeDoc
from app.models.level_def import LevelDef
from app.models.login_streak_rule import LoginStreakRule
from app.models.notification import Notification
from app.models.paper import Paper
from app.models.paper_question import PaperQuestion
from app.models.qq_binding import QqBinding
from app.models.question import Question
from app.models.question_bank import QuestionBank
from app.models.review import Review
from app.models.student import Student
from app.models.student_daily_xp import StudentDailyXp
from app.models.teacher import Teacher
from app.models.xp_config import XpConfig
from app.models.xp_ledger import XpLedger
from app.models.xp_limit_config import XpLimitConfig

__all__ = [
    "Base",
    "Teacher",
    "Class",
    "ClassBotConfig",
    "BotNotice",
    "Notification",
    "ClassInvite",
    "ClassXpSwitch",
    "Student",
    "StudentDailyXp",
    "XpLedger",
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
    "QuestionBank",
    "Question",
    "Paper",
    "PaperQuestion",
    "Attempt",
    "AnswerRecord",
    "Review",
]
