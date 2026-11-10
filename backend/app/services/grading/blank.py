"""填空题三档严格度：strict / smart / ai（Jev noul，阈值 0.85）。"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from app.config import get_settings
from app.services.grading.confidence import compose_confidence, needs_review
from app.services.llm.jev_client import JEV_TRUE_THRESHOLD, JevClient, JevUnavailable

BLANK_MODES = ("strict", "smart", "ai")
_NUMERIC_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?$")


@dataclass
class BlankOutcome:
    score: float
    full_score: float
    correct: bool
    basis: str
    deductions: list[str] = field(default_factory=list)
    confidence: float = 1.0
    needs_review: bool = False
    engine: str = "deterministic"
    degraded: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


def normalize_strict(value: Any) -> str:
    """严格：去空白后全等（保留大小写/全半角/标点）。"""
    return "".join(str(value if value is not None else "").split())


def _as_decimal(value: Any) -> Decimal | None:
    text = unicodedata.normalize("NFKC", str(value if value is not None else "")).strip().replace(",", "")
    if not _NUMERIC_RE.match(text):
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def normalize_smart(value: Any) -> str:
    """智能宽松：忽略大小写/全半角/标点/空格；数字用 Decimal 归一。"""
    number = _as_decimal(value)
    if number is not None:
        return f"num:{number.normalize()}"
    text = unicodedata.normalize("NFKC", str(value if value is not None else "")).casefold()
    return "".join(
        ch for ch in text if not ch.isspace() and not unicodedata.category(ch).startswith("P")
    )


def smart_equal(standard: Any, student: Any) -> bool:
    expected = _as_decimal(standard)
    actual = _as_decimal(student)
    if expected is not None and actual is not None:
        return expected == actual
    return normalize_smart(standard) == normalize_smart(student)


def build_jev_state(*, question: str, standard: Any, student: Any) -> str:
    """Jev 官方 state：题干 + 标准答案 + 学生答案，不使用 messages。"""
    return (
        f"题干：{question or '（未提供题干）'}\n"
        f"标准答案：{standard}\n"
        f"学生答案：{student}"
    )


def build_jev_questions(key: str = "blank") -> dict[str, dict[str, Any]]:
    return {
        key: {
            "type": "noul",
            "instructions": "判断学生答案与标准答案是否语义等价",
            "criteria": {"true": "语义等价", "false": "不等价"},
        }
    }


def _deterministic(student: Any, standard: Any, full_score: float, *, mode: str) -> BlankOutcome:
    if mode == "strict":
        correct = normalize_strict(standard) == normalize_strict(student)
        basis = "填空严格：去空白后全等"
    else:
        correct = smart_equal(standard, student)
        basis = "填空智能宽松：忽略大小写/全半角/标点/空格，数字等价"
    return BlankOutcome(
        score=round(float(full_score if correct else 0.0), 2),
        full_score=round(float(full_score), 2),
        correct=correct,
        basis=basis,
        deductions=[] if correct else ["答案不等价"],
        confidence=1.0,
        needs_review=False,
        engine="deterministic",
        degraded=False,
    )


def _fallback_deterministic(
    *, standard: Any, student: Any, full_score: float, reason: str
) -> BlankOutcome:
    outcome = _deterministic(student, standard, full_score, mode="smart")
    outcome.engine = "deterministic"
    outcome.degraded = True
    outcome.needs_review = True
    outcome.confidence = 0.0
    outcome.basis = f"{outcome.basis}；AI 不可用，降级确定性判分（{reason}）"
    outcome.raw = {"fallback": {"reason": reason, "engine": "deterministic"}}
    return outcome


def _fallback_llm(
    *,
    standard: Any,
    student: Any,
    full_score: float,
    question: str,
    llm_router: Any,
) -> BlankOutcome | None:
    if llm_router is None:
        return None
    messages = [
        {"role": "system", "content": "你是判分助手，只输出 true 或 false，不要解释。"},
        {
            "role": "user",
            "content": (
                f"题干：{question or '（未提供题干）'}\n"
                f"标准答案：{standard}\n学生答案：{student}\n"
                "学生答案与标准答案语义等价吗？只回答 true/false。"
            ),
        },
    ]
    try:
        result = llm_router.chat(messages, temperature=0, max_tokens=8)
    except Exception:  # noqa: BLE001 - 通用池失败继续降级
        return None
    text = (result.content or "").strip().lower()
    if "true" in text or text in ("yes", "1", "是", "等价"):
        correct = True
    elif "false" in text or text in ("no", "0", "否", "不等价"):
        correct = False
    else:
        correct = False
    confidence = compose_confidence(0.0, 1.0, 0.0)
    return BlankOutcome(
        score=round(float(full_score if correct else 0.0), 2),
        full_score=round(float(full_score), 2),
        correct=correct,
        basis=f"填空 AI 语义等价（通用池兜底）：{question or '未提供题干'}",
        deductions=[] if correct else ["通用池判定不等价"],
        confidence=confidence,
        needs_review=True,
        engine="llm",
        degraded=True,
        raw={
            "llm": {
                "provider": getattr(result, "provider", None),
                "model": getattr(result, "model", None),
                "degraded": True,
            }
        },
    )


def grade_blank(
    *,
    standard: Any,
    student: Any,
    full_score: float = 1.0,
    mode: str = "smart",
    question: str = "",
    jev_client: JevClient | None = None,
    llm_router: Any = None,
    fallback_to_llm: bool | None = None,
) -> BlankOutcome:
    """三档判分；ai 失败按配置走通用池/确定性，并明确 degraded。"""
    normalized_mode = (mode or "smart").strip().lower()
    if normalized_mode not in BLANK_MODES:
        raise ValueError(f"unsupported blank mode: {mode!r}")
    if normalized_mode in ("strict", "smart"):
        return _deterministic(student, standard, full_score, mode=normalized_mode)

    settings = get_settings()
    allow_llm = settings.jev_fallback_to_llm if fallback_to_llm is None else fallback_to_llm
    if jev_client is None or not jev_client.available():
        return _fallback_with_llm_or_deterministic(
            standard=standard,
            student=student,
            full_score=full_score,
            question=question,
            llm_router=llm_router,
            allow_llm=allow_llm,
            reason="disabled_or_missing_appkey",
        )

    try:
        result = jev_client.evaluate(
            state=build_jev_state(question=question, standard=standard, student=student),
            questions=build_jev_questions(),
        )
    except JevUnavailable as exc:
        return _fallback_with_llm_or_deterministic(
            standard=standard,
            student=student,
            full_score=full_score,
            question=question,
            llm_router=llm_router,
            allow_llm=allow_llm,
            reason=exc.reason,
        )

    answer = result.answers.get("blank")
    if answer is None:
        return _fallback_with_llm_or_deterministic(
            standard=standard,
            student=student,
            full_score=full_score,
            question=question,
            llm_router=llm_router,
            allow_llm=allow_llm,
            reason="missing_blank_answer",
        )
    correct = answer.as_bool(JEV_TRUE_THRESHOLD)
    confidence = compose_confidence(answer.confidence, 1.0, 0.0)
    # 模型自身置信度偏低时也进入人工复核（M2B 低置信样本口径）
    review = needs_review(confidence) or float(answer.confidence) < 0.6
    return BlankOutcome(
        score=round(float(full_score if correct else 0.0), 2),
        full_score=round(float(full_score), 2),
        correct=correct,
        basis=f"填空 AI 语义等价（Jev noul，阈值 {JEV_TRUE_THRESHOLD}）",
        deductions=[] if correct else ["Jev 判定不等价"],
        confidence=confidence,
        needs_review=review,
        engine="jev",
        degraded=False,
        raw={
            "jev": {
                "type": answer.type,
                "confidence": answer.confidence,
                "noul": answer.noul,
                "probabilities": answer.probabilities,
                "transport": result.transport,
            }
        },
    )


def _fallback_with_llm_or_deterministic(
    *,
    standard: Any,
    student: Any,
    full_score: float,
    question: str,
    llm_router: Any,
    allow_llm: bool,
    reason: str,
) -> BlankOutcome:
    if allow_llm:
        llm_outcome = _fallback_llm(
            standard=standard,
            student=student,
            full_score=full_score,
            question=question,
            llm_router=llm_router,
        )
        if llm_outcome is not None:
            llm_outcome.raw.setdefault("fallback", {"from": "jev", "reason": reason})
            return llm_outcome
    return _fallback_deterministic(standard=standard, student=student, full_score=full_score, reason=reason)
