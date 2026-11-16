"""M3.5 群内 AI 问答：班级知识检索 + 模式控制 + 10 秒限流。"""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from concurrent.futures import as_completed

from loguru import logger
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.class_bot_config import ClassBotConfig
from app.models.knowledge_chunk import KnowledgeChunk
from app.services.llm.base import AllProvidersFailed, LLMResult
from app.services.llm.router import build_router
from app.utils import cache_keys

UNKNOWN_HELP = "未识别命令。发送“帮助”查看可用命令。"
UNAVAILABLE = "我暂时没查到，换个问法或发送 帮助。"
RATE_LIMITED = "请 10 秒后再问，避免刷屏。"

_SMALL_TALK_RE = re.compile(
    r"^(你好|您好|泥嚎|哈喽|嗨|hi|hello|在吗|在不在|谢谢|谢啦|"
    r"早上好|下午好|晚上好|晚安|拜拜|再见)[呀啊哦呢嘛啦]*[!！。，,~～\s]*$",
    re.IGNORECASE,
)
_SMALL_TALK_REPLY = (
    "你好呀，我是小芽。\n"
    "可以直接问班级资料、作业思路或知识点；需要命令清单就发送“帮助”。"
)

_QQ_CHUNK_CHARS = 1000
_QQ_MAX_CHUNKS = 5


def format_for_qq(text: str) -> str:
    """把 LLM 的 markdown/LaTeX 转成 QQ 群能直接读的纯文本。"""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(
        r"```[^\n]*\n(.*?)```",
        lambda match: "代码：\n" + match.group(1).strip(),
        text,
        flags=re.S,
    )
    text = re.sub(r"`([^`\n]+)`", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text, flags=re.S)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", text)
    text = re.sub(r"^\s*[-*+]\s+", "· ", text, flags=re.M)
    text = re.sub(r"^\s*>\s?", "", text, flags=re.M)
    text = re.sub(r"^\s*---+\s*$", "————", text, flags=re.M)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1（\2）", text)
    # LaTeX 在 QQ 不渲染，去掉定界符并把常见命令换成可读符号
    text = text.replace("\\(", "").replace("\\)", "")
    text = text.replace("\\[", "").replace("\\]", "")
    text = text.replace("\\equiv", "≡").replace("\\mid", "|").replace("\\cdot", "·")
    text = re.sub(r"\\pmod\s*\{?([^{}\s]+)\}?", r"（mod \1）", text)
    text = re.sub(r"\\(?:text|mathrm|mathbf)\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\[A-Za-z]+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_for_qq(text: str, *, limit: int = _QQ_CHUNK_CHARS) -> list[str]:
    """按段落/句子切成多条，避免 QQ 单条 600 字左右被截断。"""
    body = (text or "").strip()
    if not body:
        return []
    chunks: list[str] = []
    rest = body
    while rest and len(chunks) < _QQ_MAX_CHUNKS:
        if len(rest) <= limit:
            chunks.append(rest.strip())
            break
        window = rest[:limit]
        cut = max(window.rfind("\n"), window.rfind("。"), window.rfind("！"), window.rfind("？"))
        if cut < limit // 2:
            cut = limit
        else:
            cut += 1
        chunk = rest[:cut].strip()
        if chunk:
            chunks.append(chunk)
        rest = rest[cut:].lstrip()
    if rest and len(chunks) >= _QQ_MAX_CHUNKS:
        chunks[-1] = chunks[-1].rstrip() + "\n…（内容较长，已截断）"
    return chunks


def _redis():
    from app.redis_client import get_redis_client

    return get_redis_client()


def _terms(question: str) -> list[str]:
    raw = re.findall(r"[A-Za-z0-9]{2,}|[\u4e00-\u9fff]{2,}", question or "")
    terms: list[str] = []
    for token in raw:
        candidates = [token] if token.isascii() else []
        if not token.isascii():
            for size in (4, 3, 2):
                candidates.extend(token[i : i + size] for i in range(0, len(token), max(1, size)))
        for item in candidates:
            item = item.strip()
            if len(item) >= 2 and item not in terms:
                terms.append(item)
    return terms[:8]


def retrieve_chunks(db: Session, *, class_id: int, question: str, limit: int = 4) -> list[KnowledgeChunk]:
    terms = _terms(question)
    query = db.query(KnowledgeChunk).filter(KnowledgeChunk.class_id == class_id)
    if terms:
        query = query.filter(
            or_(
                *(
                    [KnowledgeChunk.content.contains(term, autoescape=True) for term in terms]
                    + [KnowledgeChunk.doc_name.contains(term, autoescape=True) for term in terms]
                )
            )
        )
    else:
        query = query.filter(KnowledgeChunk.content.contains((question or "")[:20], autoescape=True))
    return query.order_by(KnowledgeChunk.id.asc()).limit(limit).all()


def _allow(openid: str) -> bool:
    try:
        return bool(_redis().set(cache_keys.bot_chat_key(openid), "1", nx=True, ex=10))
    except Exception:  # noqa: BLE001 - Redis 故障不阻塞问答
        return True


def _race_chat(router, messages: list[dict[str, str]], **kwargs) -> LLMResult:
    """多个 provider 并行竞速，先成功者胜；整体等待上限由 provider timeout 控制。"""
    providers = list(getattr(router, "providers", []) or [])
    if len(providers) < 2:
        return router.chat(messages, **kwargs)
    for provider in providers:
        if hasattr(provider, "max_retries"):
            provider.max_retries = 0
    errors: list[dict[str, object]] = []
    pool = ThreadPoolExecutor(max_workers=len(providers), thread_name_prefix="bot-llm")
    futures = {pool.submit(provider.chat, messages, **kwargs): provider.name for provider in providers}
    try:
        for future in as_completed(futures, timeout=9):
            name = futures[future]
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001 - 竞速失败继续等其他 provider
                errors.append({"provider": name, "error": type(exc).__name__})
                continue
            if result.content and result.content.strip():
                return result
    except FuturesTimeout:
        errors.append({"provider": "*", "error": "race_timeout"})
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    raise AllProvidersFailed(errors)


def answer(
    db: Session,
    *,
    config: ClassBotConfig,
    class_id: int,
    openid: str,
    question: str,
) -> str:
    if not config.bot_chat_enabled:
        return UNKNOWN_HELP
    mode = (config.bot_chat_mode or "balanced").lower()
    if mode == "strict":
        return UNKNOWN_HELP
    if _SMALL_TALK_RE.match((question or "").strip()):
        # 问候/寒暄不消耗 LLM；QQ 群内要的是即时感
        return _SMALL_TALK_REPLY
    if not _allow(openid):
        return RATE_LIMITED
    max_chars = max(100, min(2000, int(config.bot_chat_max_chars or 1200)))
    chunks: list[KnowledgeChunk] = []
    if mode != "free":
        try:
            chunks = retrieve_chunks(db, class_id=class_id, question=question)
        except Exception as exc:  # noqa: BLE001
            logger.warning("bot chat retrieval failed: {}", type(exc).__name__)
    context = ""
    if chunks:
        context = "\n\n".join(
            f"[来源：{chunk.doc_name}]\n{chunk.content[:1200]}" for chunk in chunks
        )
    system = (
        "你是青芽 SproutLearn 的班级 AI 助教。优先基于提供的班级资料回答；"
        "资料不足时可以自由回答，但不得编造学校制度、政策或未提供的资料。"
        "不要直接给正在考试/作业的答案，只给思路和知识点。"
        "不要使用 Markdown 标记、代码围栏或 LaTeX 定界符，直接输出适合聊天窗口阅读的中文纯文本。"
        f"用中文回答，控制在 {max_chars} 字以内。"
    )
    user = (
        f"班级资料：\n{context}\n\n学生问题：{question}"
        if context
        else f"学生问题：{question}"
    )
    try:
        started = time.perf_counter()
        settings = get_settings()
        try:
            # 群聊问答并行竞速：整体约 8 秒内拿到第一个可用回答
            settings = settings.model_copy(
                update={
                    "llm_timeout_seconds": 8,
                    "llm_chain": "deepseek,amd,zhipu",
                }
            )
        except Exception:  # noqa: BLE001 - 老版本 Settings 无 model_copy 时用原配置
            pass
        router = build_router(settings)
        result = _race_chat(
            router,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=min(1200, max(96, max_chars)),
        )
        content = (result.content or "").strip()
        if not content:
            return UNAVAILABLE
        logger.info(
            "bot chat answered openid={} mode={} elapsed_ms={}",
            openid,
            mode,
            round((time.perf_counter() - started) * 1000, 1),
        )
        # 给模型留出把一句话讲完的空间；超长时由 gateway 按语义分条，不在这里硬断句
        return format_for_qq(content)[: max_chars * 2]
    except Exception as exc:  # noqa: BLE001 - 机器人不能因 LLM 失败抛栈
        logger.warning("bot chat llm failed openid={} error={}", openid, type(exc).__name__)
        return UNAVAILABLE
