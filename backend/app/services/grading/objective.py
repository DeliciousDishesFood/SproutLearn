"""客观题确定性判分：单选/判断/多选。多选本轮全对得分。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ObjectiveOutcome:
    score: float
    full_score: float
    correct: bool
    basis: str
    deductions: list[str] = field(default_factory=list)


def _text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def _choice_set(value: Any) -> set[str]:
    """把 'A,B' / ['A','B'] / 'AB' 统一成大写选项集合。"""
    if isinstance(value, (list, tuple, set)):
        raw = [str(item) for item in value]
    else:
        text = _text(value)
        if "," in text or "，" in text or ";" in text or "；" in text:
            raw = [item for item in text.replace("，", ",").replace("；", ";").replace(";", ",").split(",")]
        elif len(text) > 1 and all(ch.isalpha() for ch in text):
            raw = list(text)
        else:
            raw = [text]
    return {item.strip().upper() for item in raw if item.strip()}


def _truth(value: Any) -> bool | None:
    text = _text(value).lower()
    if text in {"true", "t", "1", "yes", "y", "对", "正确", "是"}:
        return True
    if text in {"false", "f", "0", "no", "n", "错", "错误", "否"}:
        return False
    return None


def grade_single_choice(standard: Any, student: Any, full_score: float = 1.0) -> ObjectiveOutcome:
    expected = _text(standard).upper()
    actual = _text(student).upper()
    correct = bool(expected) and expected == actual
    return ObjectiveOutcome(
        score=round(float(full_score if correct else 0.0), 2),
        full_score=round(float(full_score), 2),
        correct=correct,
        basis=f"单选：标准 {expected or '∅'}，学生 {actual or '∅'}",
        deductions=[] if correct else ["选项不一致"],
    )


def grade_true_false(standard: Any, student: Any, full_score: float = 1.0) -> ObjectiveOutcome:
    expected = _truth(standard)
    actual = _truth(student)
    correct = expected is not None and expected == actual
    return ObjectiveOutcome(
        score=round(float(full_score if correct else 0.0), 2),
        full_score=round(float(full_score), 2),
        correct=correct,
        basis=f"判断：标准 {expected}，学生 {actual}",
        deductions=[] if correct else ["判断结果不一致"],
    )


def grade_multiple_choice(standard: Any, student: Any, full_score: float = 1.0) -> ObjectiveOutcome:
    """多选：全对得分，漏选/错选 0 分（Q4 已决）。"""
    expected = _choice_set(standard)
    actual = _choice_set(student)
    correct = bool(expected) and expected == actual
    deductions = []
    if not correct:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            deductions.append(f"漏选：{','.join(missing)}")
        if extra:
            deductions.append(f"错选：{','.join(extra)}")
        if not deductions:
            deductions.append("多选答案为空")
    return ObjectiveOutcome(
        score=round(float(full_score if correct else 0.0), 2),
        full_score=round(float(full_score), 2),
        correct=correct,
        basis=f"多选：标准 {','.join(sorted(expected)) or '∅'}，学生 {','.join(sorted(actual)) or '∅'}；全对得分口径",
        deductions=deductions,
    )


def grade_objective(
    question_type: str,
    standard: Any,
    student: Any,
    full_score: float = 1.0,
) -> ObjectiveOutcome:
    """按题型分发；未知题型抛 ValueError，由上层转 40001/配置错误。"""
    kind = (question_type or "").strip().lower()
    if kind in ("single_choice", "single", "choice"):
        return grade_single_choice(standard, student, full_score)
    if kind in ("true_false", "judge", "boolean"):
        return grade_true_false(standard, student, full_score)
    if kind in ("multiple_choice", "multiple", "multi_choice"):
        return grade_multiple_choice(standard, student, full_score)
    raise ValueError(f"unsupported objective question type: {question_type!r}")
