"""模型路由：顺序降级、审计、熔断（内存态）。"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from loguru import logger

from app.config import Settings, get_settings
from app.services.llm.base import AllProvidersFailed, LLMProvider, LLMResult
from app.services.llm.errors import LLMError
from app.services.llm.registry import build_chain

BREAKER_THRESHOLD = 3
BREAKER_COOLDOWN_SECONDS = 60.0


@dataclass
class CircuitState:
    failures: int = 0
    open_until: float = 0.0


@dataclass
class ModelRouter:
    """按配置顺序调用 provider；失败切换并写 JSON 审计。"""

    providers: list[LLMProvider]
    breaker_threshold: int = BREAKER_THRESHOLD
    breaker_cooldown_seconds: float = BREAKER_COOLDOWN_SECONDS
    clock: Callable[[], float] = time.monotonic
    audit_sink: list[dict[str, Any]] | None = None
    _circuits: dict[str, CircuitState] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._circuits = {provider.name: CircuitState() for provider in self.providers}

    def _audit(self, from_name: str | None, to_name: str | None, reason: str, attempt: int) -> None:
        event = {
            "from": from_name,
            "to": to_name,
            "reason": reason,
            "attempt": attempt,
        }
        if self.audit_sink is not None:
            self.audit_sink.append(event)
        logger.info("llm_route_switch {}", json.dumps(event, ensure_ascii=False, sort_keys=True))

    def _state(self, name: str) -> CircuitState:
        return self._circuits.setdefault(name, CircuitState())

    def breaker_open(self, name: str) -> bool:
        """查询某厂商是否在熔断窗口内；窗口过期自动复位。"""
        state = self._state(name)
        now = self.clock()
        if state.open_until and now < state.open_until:
            return True
        if state.open_until and now >= state.open_until:
            state.open_until = 0.0
            state.failures = 0
        return False

    def _record_failure(self, name: str) -> None:
        state = self._state(name)
        state.failures += 1
        if state.failures >= self.breaker_threshold:
            state.open_until = self.clock() + self.breaker_cooldown_seconds
            state.failures = 0
            logger.warning("llm_circuit_open provider={} cooldown={}s", name, self.breaker_cooldown_seconds)

    def _record_success(self, name: str) -> None:
        state = self._state(name)
        state.failures = 0
        state.open_until = 0.0

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> LLMResult:
        """依次尝试；成功返回 LLMResult，全部失败抛 AllProvidersFailed。"""
        if not self.providers:
            raise AllProvidersFailed([])

        audit: list[dict[str, Any]] = self.audit_sink if self.audit_sink is not None else []
        first_name = self.providers[0].name
        previous: str | None = "start"
        degraded = False
        errors: list[dict[str, Any]] = []

        for index, provider in enumerate(self.providers, start=1):
            name = provider.name
            if not provider.available():
                self._audit(previous, name, "no_api_key", index)
                errors.append({"provider": name, "reason": "no_api_key", "attempt": index})
                degraded = True
                previous = name
                continue
            if self.breaker_open(name):
                self._audit(previous, name, "circuit_open", index)
                errors.append({"provider": name, "reason": "circuit_open", "attempt": index})
                degraded = True
                previous = name
                continue

            try:
                result = provider.chat(messages, **kwargs)
                self._record_success(name)
                result.degraded = degraded or index > 1
                result.fallback_from = first_name if result.degraded else None
                return result
            except LLMError as exc:
                self._record_failure(name)
                next_name = self.providers[index].name if index < len(self.providers) else None
                self._audit(name, next_name, exc.category, index)
                errors.append({"provider": name, "reason": exc.category, "attempt": index})
                degraded = True
                previous = name
            except Exception as exc:  # noqa: BLE001 - 未知异常按上游失败处理
                self._record_failure(name)
                next_name = self.providers[index].name if index < len(self.providers) else None
                self._audit(name, next_name, LLMError.SERVER_ERROR, index)
                errors.append({"provider": name, "reason": LLMError.SERVER_ERROR, "attempt": index})
                logger.warning("llm_provider_unexpected provider={} error={}", name, type(exc).__name__)
                degraded = True
                previous = name

        raise AllProvidersFailed(errors or audit)


def build_router(settings: Settings | None = None) -> ModelRouter:
    """从 Settings 构造路由；测试可传入自定义 providers。"""
    current = settings or get_settings()
    return ModelRouter(providers=build_chain(current))
