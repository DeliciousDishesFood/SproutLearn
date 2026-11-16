"""M3.6 练习页「问问小芽」：苏格拉底式引导，严格不泄漏标准答案。

与 QQ 群问答（bot_chat_service）复用同一套检索、并行竞速与纯文本清洗能力，
但本服务面向学生作答页，prompt 只允许使用题干/选项/知识点，
绝不读取或拼接 answer_json、analysis 等正确答案字段。
"""

from __future__ import annotations

from datetime import date
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CurrentUser
from app.exceptions import AppException, ErrorCode
from app.models.paper import Paper
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.paper_repo import PaperRepository
from app.schemas.attempt import AskSproutRequest
from app.services import bot_chat_service
from app.services.llm.base import AllProvidersFailed
from app.services.llm.router import build_router
from app.utils import cache_keys

COOLDOWN_SECONDS = 3
DAILY_LIMIT = 40
DAILY_WINDOW_SECONDS = 24 * 3600
MAX_HISTORY = 6
MAX_ANSWER_CHARS = 600

SYSTEM_PROMPT = (
    "你是青芽 SproutLearn 练习页的 AI 助教「小芽」。请用苏格拉底式提问引导学生自己思考："
    "先点出题目涉及的知识点，再给思路提示与追问，不要直接给出最终答案；"
    "选择题不要直接说出选项字母或正确选项内容；填空题不要直接给出应填内容；"
    "不得编造学校制度、考试政策或未提供的资料；"
    "不要使用 Markdown 标记、代码围栏或 LaTeX 定界符，直接输出适合聊天窗口阅读的中文纯文本，"
    f"回答控制在 {MAX_ANSWER_CHARS} 字以内。"
)


def _redis():
    from app.redis_client import get_redis_client

    return get_redis_client()


def _check_rate_limit(student_id: int) -> None:
    """同学生 3 秒 1 次 + 每天 40 次；Redis 故障时降级放行。"""
    try:
        client = _redis()
        cooldown_key = cache_keys.ask_sprout_cooldown_key(student_id)
        if not client.set(cooldown_key, "1", nx=True, ex=COOLDOWN_SECONDS):
            raise AppException(ErrorCode.RATE_LIMITED, "操作过于频繁，请 3 秒后再问")
        daily_key = cache_keys.ask_sprout_daily_key(student_id, date.today().isoformat())
        count = client.incr(daily_key)
        if count == 1:
            client.expire(daily_key, DAILY_WINDOW_SECONDS)
        if count > DAILY_LIMIT:
            raise AppException(ErrorCode.RATE_LIMITED, "今日提问次数已达上限，请明天再来")
    except AppException:
        raise
    except Exception as exc:  # noqa: BLE001 - Redis 故障不阻塞练习问答
        logger.warning("ask sprout redis unavailable, degrade to allow: {}", type(exc).__name__)


def _load_attempt(db: Session, current: CurrentUser, attempt_id: int):
    attempt = AttemptRepository(db).get_by_id(attempt_id)
    if attempt is None:
        raise AppException(ErrorCode.NOT_FOUND, "作答记录不存在")
    paper = db.get(Paper, attempt.paper_id)
    if paper is None:
        raise AppException(ErrorCode.NOT_FOUND, "试卷不存在")
    if attempt.student_id != current.user_id or attempt.class_id != current.class_id:
        raise AppException(ErrorCode.CLASS_FORBIDDEN, "无权访问该作答记录")
    return attempt, paper


def _format_options(options: Any) -> str:
    if not options:
        return "（无选项）"
    lines: list[str] = []
    for opt in options:
        if isinstance(opt, dict):
            key = opt.get("key") or opt.get("label") or ""
            text = opt.get("text") or opt.get("content") or ""
            lines.append(f"{key}. {text}".strip())
        else:
            lines.append(str(opt))
    return "\n".join(lines).strip() or "（无选项）"


def _build_context(chunks: list[Any]) -> str:
    if not chunks:
        return ""
    return "\n\n".join(
        f"[来源：{chunk.doc_name}]\n{chunk.content[:1200]}" for chunk in chunks
    )


def _build_sources(chunks: list[Any]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    seen: set[int] = set()
    for chunk in chunks:
        doc_id = int(chunk.doc_id)
        if doc_id in seen:
            continue
        seen.add(doc_id)
        sources.append({"doc_id": doc_id, "doc_name": str(chunk.doc_name)})
    return sources


def ask_sprout(
    db: Session,
    current: CurrentUser,
    *,
    attempt_id: int,
    payload: AskSproutRequest,
) -> dict[str, Any]:
    """POST /attempts/{attempt_id}/ask 业务入口。"""
    selected_text = (payload.selected_text or "").strip()
    if not selected_text:
        raise AppException(ErrorCode.VALIDATION_ERROR, "请先选中题目内容再提问", http_status=400)
    if not (payload.message or "").strip():
        raise AppException(ErrorCode.VALIDATION_ERROR, "问题不能为空", http_status=400)

    attempt, paper = _load_attempt(db, current, attempt_id)

    if attempt.status != "doing":
        raise AppException(ErrorCode.ATTEMPT_SUBMITTED, "本次作答已结束，小芽暂不开放")
    if (paper.kind or "practice") != "practice":
        raise AppException(ErrorCode.ROLE_FORBIDDEN, "当前不是练习模式，小芽暂不开放")

    rows = PaperRepository(db).questions(paper.id)
    question_map = {question.id: question for _pq, question in rows}
    question = question_map.get(payload.question_id)
    if question is None:
        raise AppException(ErrorCode.NOT_FOUND, "题目不属于该试卷")

    _check_rate_limit(current.user_id)

    # 检索复用 QQ 问答的公共实现；资料缺失不阻塞引导
    chunks: list[Any] = []
    try:
        chunks = bot_chat_service.retrieve_chunks(
            db,
            class_id=attempt.class_id,
            question=payload.message,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("ask sprout retrieval failed: {}", type(exc).__name__)

    context = _build_context(chunks)
    history = payload.history[-MAX_HISTORY:]

    parts = [
        f"【题目】{question.stem}",
        f"【选项】\n{_format_options(question.options_json)}",
        f"【知识点】{question.knowledge_tag or '未分类'}",
        f"【学生选中的内容】{selected_text}",
        f"【学生的问题】{payload.message}",
    ]
    if context:
        parts.append(f"【班级参考资料】\n{context}")
    if history:
        history_lines = [
            f"{'学生' if item.role == 'user' else '小芽'}：{item.content}" for item in history
        ]
        parts.append("【最近对话记录】\n" + "\n".join(history_lines))

    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history:
        messages.append({"role": item.role, "content": item.content})
    messages.append({"role": "user", "content": "\n".join(parts)})

    try:
        settings = get_settings()
        try:
            settings = settings.model_copy(
                update={"llm_timeout_seconds": 8, "llm_chain": "deepseek,amd,zhipu"}
            )
        except Exception:  # noqa: BLE001 - 老版本 Settings 无 model_copy 时用原配置
            pass
        router = build_router(settings)
        result = bot_chat_service._race_chat(
            router,
            messages,
            temperature=0.3,
            max_tokens=512,
        )
        answer = bot_chat_service.format_for_qq(result.content or "")
        if not answer:
            raise AppException(ErrorCode.DEPENDENCY_UNAVAILABLE, "小芽暂时没有思路，请稍后再问")
    except AppException:
        raise
    except AllProvidersFailed as exc:
        logger.warning("ask sprout all providers failed: {}", type(exc).__name__)
        raise AppException(ErrorCode.DEPENDENCY_UNAVAILABLE, "小芽暂时不可用，请稍后再试") from exc
    except Exception as exc:  # noqa: BLE001 - 接口不能因 LLM 异常抛栈
        logger.warning("ask sprout llm failed: {}", type(exc).__name__)
        raise AppException(ErrorCode.DEPENDENCY_UNAVAILABLE, "小芽暂时不可用，请稍后再试") from exc

    return {
        "answer": answer[:MAX_ANSWER_CHARS],
        "sources": _build_sources(chunks),
    }
