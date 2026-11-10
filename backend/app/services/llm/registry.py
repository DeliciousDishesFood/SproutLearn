"""厂商注册表：按标识构造 provider，未知标识启动即报错。"""

from __future__ import annotations

from app.config import Settings, get_settings
from app.services.llm.base import LLMProvider
from app.services.llm.errors import LLMConfigError
from app.services.llm.openai_compat import OpenAICompatProvider


def _build_amd(settings: Settings) -> LLMProvider:
    return OpenAICompatProvider(
        name="amd",
        base_url=settings.amd_base_url,
        api_key=settings.amd_api_key,
        model=settings.amd_model,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )


def _build_zhipu(settings: Settings) -> LLMProvider:
    return OpenAICompatProvider(
        name="zhipu",
        base_url=settings.zhipu_base_url,
        api_key=settings.zhipu_api_key,
        model=settings.zhipu_model,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        fallback_model=settings.zhipu_model_fallback,
    )


def _build_deepseek(settings: Settings) -> LLMProvider:
    return OpenAICompatProvider(
        name="deepseek",
        base_url=settings.deepseek_base_url,
        api_key=settings.deepseek_api_key,
        model=settings.deepseek_model,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )


_BUILDERS = {
    "amd": _build_amd,
    "zhipu": _build_zhipu,
    "deepseek": _build_deepseek,
}


def build_provider(name: str, settings: Settings | None = None) -> LLMProvider:
    """按厂商标识构造 provider；未知标识抛 LLMConfigError。"""
    key = (name or "").strip().lower()
    builder = _BUILDERS.get(key)
    if builder is None:
        raise LLMConfigError(f"unknown llm provider: {name!r}")
    return builder(settings or get_settings())


def build_chain(settings: Settings | None = None) -> list[LLMProvider]:
    """按 LLM_CHAIN 顺序构造整条链（key 为空也保留，由 router 记录跳过）。"""
    current = settings or get_settings()
    return [build_provider(name, current) for name in current.llm_chain_list]


def validate_chain(settings: Settings | None = None) -> None:
    """启动期配置校验：只构造对象，不发起网络请求。"""
    build_chain(settings)
