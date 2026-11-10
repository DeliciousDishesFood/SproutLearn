"""P1 路由测试：顺序降级、审计、跳过、熔断、未知厂商标识。"""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.services.llm.base import AllProvidersFailed, LLMResult
from app.services.llm.errors import LLMConfigError, LLMError
from app.services.llm.registry import build_provider
from app.services.llm.router import ModelRouter


class FakeProvider:
    def __init__(self, name, *, available=True, results=None):
        self.name = name
        self.model = f"{name}-model"
        self._available = available
        self.results = list(results or [])
        self.calls = 0

    def available(self):
        return self._available

    def chat(self, messages, **kwargs):
        self.calls += 1
        item = self.results.pop(0) if self.results else "ok"
        if isinstance(item, Exception):
            raise item
        return LLMResult(content=str(item), provider=self.name, model=self.model, latency_ms=1.0)


def test_router_fallback_order_and_audit():
    amd = FakeProvider("amd", results=[LLMError(LLMError.RATE_LIMITED, "429")])
    zhipu = FakeProvider("zhipu", results=["zhipu-ok"])
    deepseek = FakeProvider("deepseek", available=False)
    audit: list[dict] = []
    router = ModelRouter([amd, zhipu, deepseek], audit_sink=audit)
    result = router.chat([{"role": "user", "content": "hi"}])
    assert result.content == "zhipu-ok"
    assert result.provider == "zhipu"
    assert result.degraded is True
    assert result.fallback_from == "amd"
    assert amd.calls == 1 and zhipu.calls == 1 and deepseek.calls == 0
    assert audit[0] == {"from": "amd", "to": "zhipu", "reason": LLMError.RATE_LIMITED, "attempt": 1}


def test_router_skips_empty_key_and_records_event():
    amd = FakeProvider("amd", results=[LLMError(LLMError.SERVER_ERROR, "500")])
    zhipu = FakeProvider("zhipu", results=[LLMError(LLMError.TIMEOUT, "timeout")])
    deepseek = FakeProvider("deepseek", available=False)
    audit: list[dict] = []
    router = ModelRouter([amd, zhipu, deepseek], audit_sink=audit)
    with pytest.raises(AllProvidersFailed) as exc_info:
        router.chat([{"role": "user", "content": "hi"}])
    assert exc_info.value.attempts[-1]["reason"] == "no_api_key"
    assert any(event["to"] == "deepseek" and event["reason"] == "no_api_key" for event in audit)
    assert deepseek.calls == 0


def test_router_circuit_breaker_opens_and_recovers():
    now = [1000.0]
    amd = FakeProvider("amd", results=[LLMError(LLMError.SERVER_ERROR, "500") for _ in range(5)])
    fallback = FakeProvider("fallback", results=["ok"] * 5)
    audit: list[dict] = []
    router = ModelRouter(
        [amd, fallback],
        audit_sink=audit,
        clock=lambda: now[0],
        breaker_threshold=3,
        breaker_cooldown_seconds=60,
    )
    for _ in range(3):
        assert router.chat([{"role": "user", "content": "hi"}]).content == "ok"
    assert amd.calls == 3
    assert router.breaker_open("amd") is True

    # 第 4 次不再请求 amd，只记录 circuit_open
    assert router.chat([{"role": "user", "content": "hi"}]).content == "ok"
    assert amd.calls == 3
    assert any(event["reason"] == "circuit_open" and event["to"] == "amd" for event in audit)

    # 冷却 60s 后恢复一次请求
    now[0] += 61
    assert router.chat([{"role": "user", "content": "hi"}]).content == "ok"
    assert amd.calls == 4


def test_router_all_failed_raises_without_leaking_keys():
    amd = FakeProvider("amd", results=[LLMError(LLMError.AUTH_FAILED, "401")])
    zhipu = FakeProvider("zhipu", results=[LLMError(LLMError.SERVER_ERROR, "500")])
    router = ModelRouter([amd, zhipu])
    with pytest.raises(AllProvidersFailed) as exc_info:
        router.chat([{"role": "user", "content": "hi"}])
    text = str(exc_info.value.attempts)
    assert "secret" not in text.lower() and "api_key" not in text.lower()


def test_unknown_provider_raises_config_error():
    with pytest.raises(LLMConfigError):
        build_provider("unknown-vendor", get_settings())
