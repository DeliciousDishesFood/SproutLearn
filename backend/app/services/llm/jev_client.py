"""JevK5 判分适配器：Bearer 优先、网关兜底、严格 state/questions schema。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

import httpx

from app.config import Settings, get_settings

JEV_TRUE_THRESHOLD = 0.85


class JevUnavailable(Exception):
    """Jev 不可用；消息只含分类/状态，不含 key 或带 appKey 的 URL。"""

    def __init__(self, reason: str, *, status_code: int | None = None) -> None:
        self.reason = reason
        self.status_code = status_code
        super().__init__(f"jev_unavailable:{reason}")


@dataclass
class JevAnswer:
    """单题答案：noul / choice / score 三原语。"""

    key: str
    type: str
    confidence: float
    noul: float | bool | None = None
    choice: str | None = None
    score: float | None = None
    probabilities: dict[str, Any] = field(default_factory=dict)

    def as_bool(self, threshold: float = JEV_TRUE_THRESHOLD) -> bool:
        """noul 语义等价：数值 >= 0.85 为真；布尔值直接返回。"""
        if isinstance(self.noul, bool):
            return self.noul
        if isinstance(self.noul, (int, float)):
            return float(self.noul) >= threshold
        if isinstance(self.noul, str):
            lowered = self.noul.strip().lower()
            if lowered in ("true", "yes", "1", "是"):
                return True
            if lowered in ("false", "no", "0", "否"):
                return False
        true_prob = self.probabilities.get("true")
        if isinstance(true_prob, (int, float)):
            return float(true_prob) >= threshold
        return False

    def score_to_full(self, full_score: float) -> float:
        """把 Jev score 归一到满分。

        Jev 的 criteria levels 通常已是 0..满分；若上游返回 0..1 比例，则乘以满分。
        样本 round(1.5535, 2) = 1.55（满分 2）与契约一致。
        """
        if self.score is None:
            return 0.0
        value = float(self.score)
        if 0.0 <= value <= 1.0:
            value *= float(full_score)
        return round(value, 2)


@dataclass
class JevResult:
    answers: dict[str, JevAnswer]
    usage: dict[str, Any]
    latency_ms: float
    transport: str
    raw: dict[str, Any] = field(default_factory=dict)


class JevClient:
    """JevK5 调用客户端；业务调用点只允许在 grading/。"""

    def __init__(
        self,
        *,
        enabled: bool,
        base_url: str,
        gateway_url: str,
        appkey: str,
        model: str,
        timeout_seconds: float,
        client: httpx.Client | None = None,
    ) -> None:
        self.enabled = enabled
        self.base_url = base_url.rstrip("/")
        self.gateway_url = gateway_url.rstrip("/")
        self.appkey = appkey
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def available(self) -> bool:
        return bool(self.enabled and self.appkey and self.base_url and self.gateway_url)

    def evaluate(
        self,
        *,
        state: str,
        questions: dict[str, dict[str, Any]],
        transport: str = "auto",
    ) -> JevResult:
        """调用 Jev；auto 先 Bearer 后网关；两种都失败抛 JevUnavailable。"""
        if not self.available():
            raise JevUnavailable("disabled_or_missing_appkey")
        if not isinstance(questions, dict) or not questions:
            raise JevUnavailable("empty_questions")
        payload = {"model": self.model, "state": state, "questions": questions}

        order = ["bearer", "gateway"] if transport == "auto" else [transport]
        if any(item not in ("bearer", "gateway") for item in order):
            raise JevUnavailable("unknown_transport")
        last_error: JevUnavailable | None = None
        for item in order:
            try:
                body, latency_ms = self._post(item, payload)
                return self._parse(body, latency_ms, item)
            except JevUnavailable as exc:
                last_error = exc
                continue
        raise last_error or JevUnavailable("all_transports_failed")

    def probe(self, *, state: str, questions: dict[str, dict[str, Any]], transport: str) -> JevResult:
        """探针专用：指定单路，不做 auto 兜底。"""
        return self.evaluate(state=state, questions=questions, transport=transport)

    def _post(self, transport: str, payload: dict[str, Any]) -> tuple[dict[str, Any], float]:
        if transport == "bearer":
            url = f"{self.base_url}/v1/systemone"
            headers = {"Authorization": f"Bearer {self.appkey}", "Content-Type": "application/json"}
        else:
            url = f"{self.gateway_url}?appKey={quote(self.appkey, safe='')}"
            headers = {"Content-Type": "application/json"}
        started = time.perf_counter()
        try:
            response = self._client.post(url, json=payload, headers=headers, timeout=self.timeout_seconds)
        except httpx.TimeoutException as exc:
            raise JevUnavailable("timeout") from exc
        except httpx.HTTPError as exc:
            raise JevUnavailable(f"network:{type(exc).__name__}") from exc
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        body = _safe_json(response)
        if response.status_code in (401, 403):
            raise JevUnavailable("auth_failed", status_code=response.status_code)
        if response.status_code == 429:
            raise JevUnavailable("rate_limited", status_code=response.status_code)
        if response.status_code >= 500:
            raise JevUnavailable("server_error", status_code=response.status_code)
        if response.status_code != 200:
            raise JevUnavailable("bad_request", status_code=response.status_code)
        if not isinstance(body, dict):
            raise JevUnavailable("bad_payload")
        # 兼容 showapi 网关包装；当前 Jev 直连返回 answers 顶层
        if isinstance(body.get("showapi_res_code"), int) and body["showapi_res_code"] < 0:
            reason = "auth_failed" if body["showapi_res_code"] == -1004 else "bad_request"
            raise JevUnavailable(reason)
        wrapped = body.get("showapi_res_body")
        if isinstance(wrapped, dict) and wrapped:
            body = wrapped
        if not isinstance(body.get("answers"), dict):
            raise JevUnavailable("missing_answers")
        return body, latency_ms

    def _parse(self, body: dict[str, Any], latency_ms: float, transport: str) -> JevResult:
        answers: dict[str, JevAnswer] = {}
        for key, value in body.get("answers", {}).items():
            if not isinstance(value, dict):
                continue
            answer_type = str(value.get("type") or "")
            probabilities = value.get("probabilities")
            answers[str(key)] = JevAnswer(
                key=str(key),
                type=answer_type,
                confidence=float(value.get("confidence") or 0.0),
                noul=value.get("noul") if answer_type == "noul" else None,
                choice=str(value["choice"]) if value.get("choice") is not None else None,
                score=float(value["score"]) if value.get("score") is not None else None,
                probabilities=probabilities if isinstance(probabilities, dict) else {},
            )
        if not answers:
            raise JevUnavailable("empty_answers")
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        return JevResult(
            answers=answers,
            usage=usage,
            latency_ms=latency_ms,
            transport=transport,
            raw={
                "model": body.get("model"),
                "server_latency_ms": body.get("latency_ms"),
                "usage": usage,
            },
        )


def build_jev_client(settings: Settings | None = None) -> JevClient:
    current = settings or get_settings()
    return JevClient(
        enabled=current.jev_enabled,
        base_url=current.jev_base_url,
        gateway_url=current.jev_gateway_url,
        appkey=current.jev_appkey,
        model=current.jev_model,
        timeout_seconds=current.jev_timeout_seconds,
    )


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except Exception:  # noqa: BLE001
        return {}
