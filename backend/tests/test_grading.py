"""P3 判分测试：15 条三档严格度、客观题、阈值、置信度、降级。"""

from __future__ import annotations

import pytest

from app.services.grading.blank import grade_blank
from app.services.grading.confidence import compose_confidence, needs_review
from app.services.grading.grader import Grader
from app.services.grading.objective import grade_multiple_choice, grade_single_choice, grade_true_false
from app.services.llm.base import LLMResult
from app.services.llm.jev_client import JevAnswer, JevResult, JevUnavailable


class FakeJev:
    def __init__(self, *, noul=0.9, confidence=0.9, available=True, raises=False):
        self.noul = noul
        self.confidence = confidence
        self._available = available
        self.raises = raises
        self.calls = 0

    def available(self):
        return self._available

    def evaluate(self, *, state, questions, transport="auto"):
        self.calls += 1
        if self.raises:
            raise JevUnavailable("timeout")
        return JevResult(
            answers={
                "blank": JevAnswer(
                    key="blank",
                    type="noul",
                    confidence=self.confidence,
                    noul=self.noul,
                    probabilities={"true": self.noul, "false": 1 - self.noul},
                )
            },
            usage={},
            latency_ms=1.0,
            transport="bearer",
            raw={"model": "JevK5-V0.3"},
        )


class FakeRouter:
    def __init__(self, content="true"):
        self.content = content
        self.calls = 0

    def chat(self, messages, **kwargs):
        self.calls += 1
        return LLMResult(content=self.content, provider="amd", model="DeepSeek-V4-Flash", latency_ms=1.0)


@pytest.mark.parametrize(
    "standard,student,strict,smart",
    [
        ("ABC", "ABC", True, True),
        ("ABC", "abc", False, True),
        ("ABC", "A B C", True, True),
        ("ABC", "ＡＢＣ", False, True),
        ("ABC", "A.B.C", False, True),
        ("Hello", "hello", False, True),
        ("1", "1.0", False, True),
        ("1", "1,000", False, False),
        ("1.5", "1.50", False, True),
        ("A-B", "A_B", False, True),
        ("  A  ", "A", True, True),
        ("A", "B", False, False),
        ("中国", "中国", True, True),
        ("中国", "中國", False, False),
        ("A/B", "AB", False, True),
    ],
)
def test_blank_three_modes_15_cases(standard, student, strict, smart):
    strict_outcome = grade_blank(standard=standard, student=student, mode="strict", full_score=2)
    smart_outcome = grade_blank(standard=standard, student=student, mode="smart", full_score=2)
    assert strict_outcome.correct is strict
    assert smart_outcome.correct is smart
    assert strict_outcome.engine == "deterministic"
    assert smart_outcome.engine == "deterministic"


def test_objective_single_true_false_and_multi_all_or_nothing():
    assert grade_single_choice("A", "a", 2).correct is True
    assert grade_single_choice("A", "B", 2).score == 0
    assert grade_true_false("对", "true", 2).correct is True
    assert grade_true_false("错", "true", 2).correct is False

    assert grade_multiple_choice("A,B", "B,A", 3).score == 3
    assert grade_multiple_choice("A,B", "A", 3).score == 0
    assert grade_multiple_choice("A,B", "A,C", 3).score == 0
    assert grade_multiple_choice("A,B", "A,B,C", 3).score == 0


def test_ai_threshold_and_low_confidence_review():
    high = grade_blank(standard="2", student="2.0", mode="ai", full_score=2, jev_client=FakeJev(noul=0.85, confidence=0.9), fallback_to_llm=False)
    low = grade_blank(standard="2", student="3", mode="ai", full_score=2, jev_client=FakeJev(noul=0.849, confidence=0.9), fallback_to_llm=False)
    assert high.correct is True and high.score == 2
    assert low.correct is False and low.score == 0
    assert high.engine == "jev" and high.degraded is False

    low_conf = grade_blank(standard="2", student="2", mode="ai", full_score=2, jev_client=FakeJev(noul=0.9, confidence=0.2), fallback_to_llm=False)
    assert low_conf.needs_review is True
    assert low_conf.confidence < 0.6


def test_confidence_composition_formula():
    assert compose_confidence(1.0, 1.0, 0.0) == 1.0
    assert compose_confidence(0.5, 1.0, 0.0) == 0.7
    assert needs_review(0.5999) is True
    assert needs_review(0.6) is False


def test_jev_unavailable_degrades_to_deterministic_not_ai():
    outcome = grade_blank(
        standard="2",
        student="2",
        mode="ai",
        full_score=2,
        jev_client=FakeJev(available=False),
        fallback_to_llm=False,
    )
    assert outcome.engine == "deterministic"
    assert outcome.degraded is True
    assert outcome.needs_review is True


def test_jev_failure_can_fallback_to_llm_with_degraded_flag():
    router = FakeRouter("true")
    outcome = grade_blank(
        standard="2",
        student="2.0",
        mode="ai",
        full_score=2,
        jev_client=FakeJev(raises=True),
        llm_router=router,
        fallback_to_llm=True,
    )
    assert router.calls == 1
    assert outcome.engine == "llm"
    assert outcome.degraded is True
    assert outcome.needs_review is True
    assert outcome.correct is True


def test_grader_output_shape_and_engine_labels():
    objective = Grader().grade(
        question_type="single_choice",
        standard="A",
        student="A",
        full_score=2,
        knowledge_tags=["tcp"],
    )
    assert set(objective) == {
        "score",
        "full_score",
        "correct",
        "basis",
        "deductions",
        "knowledge_tags",
        "confidence",
        "needs_review",
        "engine",
        "degraded",
        "raw",
    }
    assert objective["engine"] == "deterministic"
    assert objective["knowledge_tags"] == ["tcp"]

    blank = Grader(jev_client=FakeJev(noul=0.9, confidence=0.9), blank_mode="ai").grade(
        question_type="blank",
        standard="2",
        student="2.0",
        full_score=2,
        question="1+1",
    )
    assert blank["engine"] == "jev"
    assert blank["degraded"] is False
    assert blank["needs_review"] is False
