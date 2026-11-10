"""置信度合成与人工复核阈值。"""

from __future__ import annotations

CONFIDENCE_THRESHOLD = 0.6
WEIGHT_JEV = 0.6
WEIGHT_COVERAGE = 0.3
WEIGHT_ANOMALY = 0.1


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def compose_confidence(jev_confidence: float, coverage: float, anomaly: float) -> float:
    """0.6*jev_conf + 0.3*coverage + 0.1*(1-anomaly)，输入按 0..1 截断。"""
    value = (
        WEIGHT_JEV * _clamp(jev_confidence)
        + WEIGHT_COVERAGE * _clamp(coverage)
        + WEIGHT_ANOMALY * (1.0 - _clamp(anomaly))
    )
    return round(_clamp(value), 4)


def needs_review(confidence: float, threshold: float = CONFIDENCE_THRESHOLD) -> bool:
    """低于阈值标记人工复核。"""
    return float(confidence) < threshold
