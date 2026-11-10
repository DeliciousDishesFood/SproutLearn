"""M2A 厂商探针：AMD / 智谱 / DeepSeek / OpenRouter / JevK5。

输出脱敏 Markdown，不打印任何 API key；默认写到临时工作区 handoff/llm-probe.md。
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings  # noqa: E402
from app.services.llm.errors import LLMError  # noqa: E402
from app.services.llm.jev_client import JevClient, JevUnavailable  # noqa: E402
from app.services.llm.openai_compat import OpenAICompatProvider  # noqa: E402

DEFAULT_OUTPUT = Path(r"E:\temporary-work\智能助学平台\handoff\llm-probe.md")


def _provider(
    name: str, base_url: str, api_key: str, model: str, timeout: float, max_retries: int
) -> OpenAICompatProvider:
    return OpenAICompatProvider(
        name=name,
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=timeout,
        max_retries=max_retries,
    )


def _models_row(provider: OpenAICompatProvider) -> tuple[str, str, str]:
    started = time.perf_counter()
    last_error: LLMError | None = None
    for attempt in range(2):
        try:
            models = provider.list_models()
            latency = round((time.perf_counter() - started) * 1000, 1)
            return "200", str(len(models)), f"{latency}ms"
        except LLMError as exc:
            last_error = exc
            if attempt == 0 and exc.category == LLMError.SERVER_ERROR:
                time.sleep(0.5)
                continue
            latency = round((time.perf_counter() - started) * 1000, 1)
            status = str(exc.status_code or exc.category)
            return status, "-", f"{latency}ms"
    latency = round((time.perf_counter() - started) * 1000, 1)
    return (str(last_error.status_code or last_error.category) if last_error else "SERVER_ERROR"), "-", f"{latency}ms"


def _direct_models_status(base_url: str, timeout: float) -> tuple[str, str]:
    started = time.perf_counter()
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/models", timeout=timeout)
        return str(response.status_code), f"{round((time.perf_counter() - started) * 1000, 1)}ms"
    except httpx.HTTPError:
        return "SERVER_ERROR", f"{round((time.perf_counter() - started) * 1000, 1)}ms"


def _chat_row(provider: OpenAICompatProvider) -> tuple[str, str, str]:
    started = time.perf_counter()
    try:
        result = provider.chat(
            [{"role": "user", "content": "Reply with OK only."}],
            temperature=0,
            max_tokens=8,
        )
        latency = round((time.perf_counter() - started) * 1000, 1)
        return "200", (result.content or "").strip()[:20] or "(empty)", f"{latency}ms"
    except LLMError as exc:
        latency = round((time.perf_counter() - started) * 1000, 1)
        status = str(exc.status_code or exc.category)
        return status, "-", f"{latency}ms"


def _jev_row(client: JevClient, transport: str) -> tuple[str, str, str]:
    started = time.perf_counter()
    last_error: JevUnavailable | None = None
    for attempt in range(2):
        try:
            result = client.probe(
                state="题干：1+1 等于多少？\n标准答案：2\n学生答案：2",
                questions={
                    "q1": {
                        "type": "noul",
                        "instructions": "判断学生答案与标准答案是否语义等价",
                        "criteria": {"true": "语义等价", "false": "不等价"},
                    }
                },
                transport=transport,
            )
            latency = round((time.perf_counter() - started) * 1000, 1)
            answer = result.answers.get("q1")
            detail = f"noul={getattr(answer, 'noul', None)}"
            return "200", detail, f"{latency}ms"
        except JevUnavailable as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(0.5)
                continue
            latency = round((time.perf_counter() - started) * 1000, 1)
            return exc.reason, "-", f"{latency}ms"
    latency = round((time.perf_counter() - started) * 1000, 1)
    return (last_error.reason if last_error else "unknown"), "-", f"{latency}ms"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    settings = get_settings()
    # 探针用于观测慢响应，给 60s；生产路由仍使用 LLM_TIMEOUT_SECONDS(15)
    probe_timeout = max(settings.llm_timeout_seconds, 60)

    amd = _provider("amd", settings.amd_base_url, settings.amd_api_key, settings.amd_model, probe_timeout, settings.llm_max_retries)
    zhipu = _provider("zhipu", settings.zhipu_base_url, settings.zhipu_api_key, settings.zhipu_model, probe_timeout, settings.llm_max_retries)
    deepseek = _provider("deepseek", settings.deepseek_base_url, settings.deepseek_api_key, settings.deepseek_model, probe_timeout, settings.llm_max_retries)
    openrouter = _provider("openrouter", settings.openrouter_base_url, settings.openrouter_api_key, "", probe_timeout, 0)

    rows: list[tuple[str, str, str, str, str]] = []
    for name, provider in (("AMD", amd), ("ZHIPU", zhipu), ("DEEPSEEK", deepseek), ("OPENROUTER", openrouter)):
        if name == "OPENROUTER" and not settings.openrouter_api_key:
            rows.append((name, "models", "skipped(no_key)", "-", "-"))
            rows.append((name, "chat", "skipped(no_key)", "-", "-"))
            continue
        if name == "DEEPSEEK" and not settings.deepseek_api_key:
            # 无 key 仍直连 /models 记录 401；chat 跳过
            status, latency = _direct_models_status(settings.deepseek_base_url, probe_timeout)
            rows.append((name, "models", status, "-", latency))
            rows.append((name, "chat", "skipped(no_key)", "-", "-"))
            continue
        status, count, latency = _models_row(provider)
        rows.append((name, "models", status, count, latency))
        if not provider.available():
            rows.append((name, "chat", "skipped(no_key)", "-", "-"))
            continue
        status, reply, latency = _chat_row(provider)
        rows.append((name, "chat", status, reply, latency))

    jev = JevClient(
        enabled=settings.jev_enabled,
        base_url=settings.jev_base_url,
        gateway_url=settings.jev_gateway_url,
        appkey=settings.jev_appkey,
        model=settings.jev_model,
        timeout_seconds=settings.jev_timeout_seconds,
    )
    for transport in ("bearer", "gateway"):
        status, detail, latency = _jev_row(jev, transport)
        rows.append(("JEV", transport, status, detail, latency))

    lines = [
        "# LLM / Jev 探针（M2A）",
        "",
        f"- 执行时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        "- 所有 key 已脱敏；网关 URL 的 appKey 不落盘。",
        "",
        "| 厂商 | 探针 | 状态 | 模型数/结果 | 延迟 |",
        "|---|---|---|---|---|",
    ]
    lines.extend(f"| {name} | {route} | {status} | {detail} | {latency} |" for name, route, status, detail, latency in rows)
    lines.extend(
        [
            "",
            "## 说明",
            "",
            "- 探针为观测慢响应使用 60s 超时；生产路由仍按 LLM_TIMEOUT_SECONDS=15 执行并会降级。",
            "- AMD models 实际返回 12 个（契约事实表写 13，2026-11-10 实测差异：`Qwen3.8-Flash-Next` 不在列表）。",
            "- DeepSeek key 为空：直连 /models 记录 401；chat 跳过，不阻塞判分主链。",
            "- OpenRouter 未配置 key：冻结，不参与调度。",
            "- Jev 采用 Bearer + 网关双路各探一次；`noul` 为归一化概率。",
            "",
        ]
    )
    text = "\n".join(lines)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    print(text)
    print(f"written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
