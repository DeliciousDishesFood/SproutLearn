"""LLM Provider 协议与统一返回结构。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class LLMResult:
    """路由成功后的固定返回结构（P1）。"""

    content: str
    provider: str
    model: str
    latency_ms: float
    degraded: bool = False
    fallback_from: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    """厂商适配器协议；实现类不得在日志/异常中输出 key。"""

    name: str
    model: str

    def available(self) -> bool:
        """配置是否具备调用条件（key 非空等）。"""

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> LLMResult:
        """调用聊天补全；失败抛 LLMError。"""


class AllProvidersFailed(Exception):
    """整条链均失败；attempts 为脱敏审计事件。"""

    def __init__(self, attempts: list[dict[str, Any]]) -> None:
        self.attempts = attempts
        super().__init__("all_llm_providers_failed")
