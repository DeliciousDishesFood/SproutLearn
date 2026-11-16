"""OpenAI 兼容厂商实现：AMD / 智谱 / DeepSeek 共用。"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from app.services.llm.base import LLMResult
from app.services.llm.errors import LLMError


def _classify_status(status_code: int) -> str:
    if status_code == 429:
        return LLMError.RATE_LIMITED
    if status_code in (401, 403):
        return LLMError.AUTH_FAILED
    if status_code >= 500:
        return LLMError.SERVER_ERROR
    return LLMError.BAD_REQUEST


def _biz_code(body: Any) -> str | None:
    if not isinstance(body, dict):
        return None
    error = body.get("error")
    if isinstance(error, dict) and error.get("code") is not None:
        return str(error["code"])
    if body.get("code") is not None:
        return str(body["code"])
    if body.get("showapi_res_code") is not None:
        return str(body["showapi_res_code"])
    return None


class OpenAICompatProvider:
    """统一 /chat/completions 客户端；错误分类 + 有限重试。"""

    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_retries: int = 1,
        fallback_model: str | None = None,
        client: httpx.Client | None = None,
        sleep_fn=time.sleep,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self.fallback_model = fallback_model
        self._client = client or httpx.Client(timeout=timeout_seconds)
        self._sleep = sleep_fn

    def available(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def list_models(self) -> list[str]:
        """GET /models，返回模型 id 列表；供探针使用。"""
        try:
            response = self._client.get(
                f"{self.base_url}/models", headers=self._headers(), timeout=self.timeout_seconds
            )
        except httpx.TimeoutException as exc:
            raise LLMError(LLMError.TIMEOUT, "models timeout") from exc
        except httpx.HTTPError as exc:
            raise LLMError(LLMError.SERVER_ERROR, type(exc).__name__) from exc
        body = _safe_json(response)
        if response.status_code != 200:
            raise LLMError(
                _classify_status(response.status_code),
                "models request failed",
                status_code=response.status_code,
                biz_code=_biz_code(body),
            )
        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, list):
            raise LLMError(LLMError.BAD_REQUEST, "models payload missing data")
        return [str(item.get("id")) for item in data if isinstance(item, dict) and item.get("id")]

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> LLMResult:
        if not self.available():
            raise LLMError(LLMError.AUTH_FAILED, "provider not configured")
        model = self.model
        last_error: LLMError | None = None
        for attempt in range(self.max_retries + 1):
            started = time.perf_counter()
            try:
                body = self._post(model, messages, kwargs)
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                return self._to_result(body, model, latency_ms)
            except LLMError as exc:
                last_error = exc
                # 智谱 1305：切备用模型；其他可重试错误退避
                if (
                    self.fallback_model
                    and self.fallback_model != model
                    and (exc.biz_code == "1305" or exc.category == LLMError.RATE_LIMITED)
                ):
                    model = self.fallback_model
                    continue
                if exc.category in (LLMError.RATE_LIMITED, LLMError.SERVER_ERROR, LLMError.TIMEOUT) and attempt < self.max_retries:
                    self._sleep(min(2 ** attempt, 2))
                    continue
                raise
        raise last_error or LLMError(LLMError.SERVER_ERROR, "unknown provider error")

    def chat_stream(self, messages: list[dict[str, str]], **kwargs: Any):
        """OpenAI SSE 流：逐段 yield delta.content；[DONE] 结束。"""
        if not self.available():
            raise LLMError(LLMError.AUTH_FAILED, "provider not configured")
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        for key in ("temperature", "max_tokens", "top_p"):
            if key in kwargs and kwargs[key] is not None:
                payload[key] = kwargs[key]
        try:
            with self._client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout_seconds,
            ) as response:
                if response.status_code != 200:
                    body = _safe_json(response)
                    raise LLMError(
                        _classify_status(response.status_code),
                        "chat stream request failed",
                        status_code=response.status_code,
                        biz_code=_biz_code(body),
                    )
                for line in response.iter_lines():
                    if not line:
                        continue
                    if isinstance(line, bytes):
                        line = line.decode("utf-8", errors="ignore")
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        body = json.loads(raw)
                    except ValueError:
                        continue
                    choices = body.get("choices") if isinstance(body, dict) else None
                    if not isinstance(choices, list) or not choices:
                        continue
                    first = choices[0] if isinstance(choices[0], dict) else {}
                    delta = first.get("delta") if isinstance(first.get("delta"), dict) else {}
                    content = delta.get("content") or delta.get("reasoning_content")
                    if isinstance(content, str) and content:
                        yield content
        except httpx.TimeoutException as exc:
            raise LLMError(LLMError.TIMEOUT, "chat stream timeout") from exc
        except httpx.HTTPError as exc:
            raise LLMError(LLMError.SERVER_ERROR, type(exc).__name__) from exc

    def _post(self, model: str, messages: list[dict[str, str]], kwargs: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": model, "messages": messages}
        for key in ("temperature", "max_tokens", "top_p"):
            if key in kwargs and kwargs[key] is not None:
                payload[key] = kwargs[key]
        try:
            response = self._client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise LLMError(LLMError.TIMEOUT, "chat timeout") from exc
        except httpx.HTTPError as exc:
            raise LLMError(LLMError.SERVER_ERROR, type(exc).__name__) from exc

        body = _safe_json(response)
        if response.status_code != 200:
            raise LLMError(
                _classify_status(response.status_code),
                "chat request failed",
                status_code=response.status_code,
                biz_code=_biz_code(body),
            )
        if not isinstance(body, dict):
            raise LLMError(LLMError.BAD_REQUEST, "chat payload not json")
        if isinstance(body.get("showapi_res_code"), int) and body["showapi_res_code"] < 0:
            raise LLMError(
                LLMError.AUTH_FAILED if body["showapi_res_code"] == -1004 else LLMError.BAD_REQUEST,
                "provider business error",
                biz_code=str(body["showapi_res_code"]),
            )
        return body

    def _to_result(self, body: dict[str, Any], model: str, latency_ms: float) -> LLMResult:
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMError(LLMError.BAD_REQUEST, "chat payload missing choices")
        first = choices[0] if isinstance(choices[0], dict) else {}
        message = first.get("message") if isinstance(first.get("message"), dict) else {}
        content = message.get("content")
        if content is None:
            content = ""
        if not isinstance(content, str):
            content = str(content)
        return LLMResult(
            content=content,
            provider=self.name,
            model=str(body.get("model") or model),
            latency_ms=latency_ms,
            raw={
                "finish_reason": first.get("finish_reason"),
                "usage": body.get("usage") if isinstance(body.get("usage"), dict) else {},
            },
        )


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except Exception:  # noqa: BLE001 - 非 JSON 响应按空对象处理
        return {}
