"""判分统一入口：题型分发 + 固定输出 + 引擎/degraded 标记。"""

from __future__ import annotations

from typing import Any

from app.services.grading.blank import grade_blank
from app.services.grading.objective import grade_objective

OBJECTIVE_TYPES = {
    "single_choice",
    "single",
    "choice",
    "true_false",
    "judge",
    "boolean",
    "multiple_choice",
    "multiple",
    "multi_choice",
}
BLANK_TYPES = {"blank", "fill_blank", "short_blank"}


class Grader:
    """M2A 判分内核；不负责 HTTP 路由与题库 CRUD。"""

    def __init__(self, *, jev_client: Any = None, llm_router: Any = None, blank_mode: str = "smart") -> None:
        self.jev_client = jev_client
        self.llm_router = llm_router
        self.blank_mode = blank_mode

    def grade(
        self,
        *,
        question_type: str,
        standard: Any,
        student: Any,
        full_score: float = 1.0,
        question: str = "",
        knowledge_tags: list[str] | None = None,
        blank_mode: str | None = None,
        fallback_to_llm: bool | None = None,
    ) -> dict[str, Any]:
        kind = (question_type or "").strip().lower()
        if kind in OBJECTIVE_TYPES:
            outcome = grade_objective(kind, standard, student, full_score)
            return {
                "score": round(outcome.score, 2),
                "full_score": round(outcome.full_score, 2),
                "correct": outcome.correct,
                "basis": outcome.basis,
                "deductions": outcome.deductions,
                "knowledge_tags": list(knowledge_tags or []),
                "confidence": 1.0,
                "needs_review": False,
                "engine": "deterministic",
                "degraded": False,
                "raw": {"standard": str(standard), "student": str(student)},
            }
        if kind in BLANK_TYPES:
            outcome = grade_blank(
                standard=standard,
                student=student,
                full_score=full_score,
                mode=blank_mode or self.blank_mode,
                question=question,
                jev_client=self.jev_client,
                llm_router=self.llm_router,
                fallback_to_llm=fallback_to_llm,
            )
            return {
                "score": round(outcome.score, 2),
                "full_score": round(outcome.full_score, 2),
                "correct": outcome.correct,
                "basis": outcome.basis,
                "deductions": outcome.deductions,
                "knowledge_tags": list(knowledge_tags or []),
                "confidence": outcome.confidence,
                "needs_review": outcome.needs_review,
                "engine": outcome.engine,
                "degraded": outcome.degraded,
                "raw": outcome.raw,
            }
        raise ValueError(f"unsupported question type: {question_type!r}")
