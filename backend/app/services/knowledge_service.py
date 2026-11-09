"""知识库业务：批量上传、逐文件独立事务、解析切片落库、列表/详情/删除。"""

from __future__ import annotations

import concurrent.futures
from time import perf_counter

from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CurrentUser
from app.exceptions import AppException, ErrorCode
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_doc import KnowledgeDoc
from app.repositories.knowledge_chunk_repo import KnowledgeChunkRepository
from app.repositories.knowledge_doc_repo import KnowledgeDocRepository
from app.services.class_service import require_owned_class
from app.strategies.parser import NoTextLayer, ParserError, get_parser
from app.strategies.storage import get_storage
from app.utils.response import page_data
from app.utils.text import char_count, sha256_hex
from app.utils.time import fmt_dt
from app.utils.validators import extract_ext, sanitize_filename

_settings = get_settings()

FileItem = tuple[str, bytes]


def _run_parser(parser, file_path: str):
    """带超时的解析调用；超时转 42202（解析线程无法强杀，仅保证请求返回）。"""
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(parser.extract, file_path)
    try:
        return future.result(timeout=_settings.parser_timeout_seconds)
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        raise ParserError("文档解析超时，请压缩文件或稍后重试") from exc
    finally:
        executor.shutdown(wait=False)


def _mark_failed(db: Session, doc_id: int, code: int, message: str) -> None:
    """解析失败后独立事务回写文档状态 3；失败不影响其他文件。"""
    try:
        db.rollback()
        doc = db.get(KnowledgeDoc, doc_id)
        if doc is None:
            return
        doc.status = 3
        doc.error_code = str(code)
        doc.error_message = (message or "文档解析失败")[:500]
        db.commit()
    except Exception as exc:  # noqa: BLE001 - 失败状态回写失败只记日志
        db.rollback()
        logger.error("回写文档失败状态失败 doc_id={}: {}", doc_id, exc)


def _create_doc(db: Session, *, class_id: int, teacher_id: int, file_name: str,
                content: bytes, file_hash: str, ext: str, course_name: str,
                file_path: str) -> KnowledgeDoc:
    doc = KnowledgeDoc(
        class_id=class_id,
        course_name=course_name,
        title=file_name[:200],
        file_name=file_name,
        file_ext=ext,
        file_size=len(content),
        file_path=file_path,
        file_hash=file_hash,
        status=1,
        chunk_count=0,
        created_by=teacher_id,
    )
    db.add(doc)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppException(ErrorCode.DOC_DUPLICATE, "文档已存在（同班同 hash）") from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(doc)
    return doc


def _ingest_document(
    db: Session,
    *,
    class_id: int,
    teacher_id: int,
    file_name: str,
    content: bytes,
    course_name: str,
) -> dict:
    """单文件独立事务：校验 → 落盘 → 建文档 → 解析 → 写切片。"""
    settings = get_settings()
    if len(file_name) > 255:
        raise AppException(ErrorCode.UNSUPPORTED_FORMAT, "文件名过长，请重命名后上传")

    ext = extract_ext(file_name)
    if ext not in settings.allowed_ext_set:
        raise AppException(ErrorCode.UNSUPPORTED_FORMAT, f"文件类型不支持: {ext or '无扩展名'}")
    if len(content) > settings.max_upload_bytes:
        raise AppException(
            ErrorCode.FILE_TOO_LARGE,
            f"文件超过 {settings.upload_max_mb}MB 上限",
        )
    if len(content) == 0:
        raise AppException(ErrorCode.PARSE_FAILED, "文件为空，无法解析")

    file_hash = sha256_hex(content)
    doc_repo = KnowledgeDocRepository(db)
    if doc_repo.exists_hash(class_id, file_hash):
        raise AppException(ErrorCode.DOC_DUPLICATE, "文档已存在（同班同 hash）")

    storage = get_storage()
    try:
        relative_path = storage.save(
            content=content, class_id=class_id, file_hash=file_hash, ext=ext
        )
    except (OSError, ValueError) as exc:
        logger.error("保存上传文件失败: {}", exc)
        raise AppException(ErrorCode.PARSE_FAILED, "文件保存失败，请稍后重试") from exc

    try:
        doc = _create_doc(
            db,
            class_id=class_id,
            teacher_id=teacher_id,
            file_name=file_name,
            content=content,
            file_hash=file_hash,
            ext=ext,
            course_name=course_name,
            file_path=relative_path,
        )
    except Exception:
        try:
            storage.delete(relative_path)
        except Exception:  # noqa: BLE001 - 清理失败只记日志
            logger.warning("回滚上传文件失败: {}", relative_path)
        raise

    started = perf_counter()
    doc_id = doc.id
    try:
        parser = get_parser(ext, settings)
        result = _run_parser(parser, storage.abspath(relative_path))
        if not result.chunks:
            raise NoTextLayer("未提取到有效文本内容")
        if result.title:
            doc.title = result.title[:200]

        chunk_rows = [
            KnowledgeChunk(
                doc_id=doc.id,
                class_id=class_id,
                doc_name=doc.title,
                chunk_index=index,
                content=chunk.content,
                char_count=char_count(chunk.content),
                chapter_title=(chunk.chapter_title[:200] if chunk.chapter_title else None),
                page_no=chunk.page_no,
            )
            for index, chunk in enumerate(result.chunks)
        ]
        db.add_all(chunk_rows)
        doc.status = 2
        doc.page_count = result.page_count
        doc.chunk_count = len(chunk_rows)
        doc.error_code = None
        doc.error_message = None
        db.commit()
        elapsed = perf_counter() - started
        if elapsed > settings.parser_timeout_seconds:
            logger.warning("文档解析耗时超过配置阈值 doc_id={} elapsed={:.1f}s", doc.id, elapsed)
        logger.info(
            "文档入库成功 doc_id={} file={} chunks={} elapsed={:.2f}s",
            doc.id,
            file_name,
            len(chunk_rows),
            elapsed,
        )
        return {
            "file_name": file_name,
            "doc_id": doc.id,
            "status": 2,
            "chunk_count": len(chunk_rows),
            "page_count": result.page_count,
        }
    except ParserError as exc:
        code = int(exc.code)
        _mark_failed(db, doc_id, code, str(exc))
        raise AppException(code, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - 单文件失败不阻塞批次
        logger.exception("文档解析异常 file={}", file_name)
        _mark_failed(db, doc_id, int(ErrorCode.PARSE_FAILED), "文档解析失败，请检查文件后重试")
        raise AppException(ErrorCode.PARSE_FAILED, "文档解析失败，请检查文件后重试") from exc


def upload_documents(
    db: Session,
    current: CurrentUser,
    *,
    class_id: int,
    course_name: str | None,
    files: list[FileItem],
) -> dict:
    """批量上传：返回 success_list / fail_list；全部失败也是 200。"""
    klass = require_owned_class(db, class_id, current.user_id)
    settings = get_settings()
    effective_course = (course_name or "").strip() or klass.course_name
    if len(effective_course) > settings.text_field_max_len:
        raise AppException(
            ErrorCode.VALIDATION_ERROR,
            f"课程名称长度必须为 1–{settings.text_field_max_len} 个字符",
        )

    success_list: list[dict] = []
    fail_list: list[dict] = []
    for raw_name, content in files:
        file_name = sanitize_filename(raw_name)
        try:
            item = _ingest_document(
                db,
                class_id=klass.id,
                teacher_id=current.user_id,
                file_name=file_name,
                content=content,
                course_name=effective_course,
            )
            success_list.append(item)
        except AppException as exc:
            db.rollback()
            fail_list.append(
                {
                    "file_name": file_name,
                    "error_code": int(exc.code),
                    "error_message": exc.message,
                }
            )
        except Exception:  # noqa: BLE001 - 兜底保证批次继续
            db.rollback()
            logger.exception("上传文件处理异常 file={}", file_name)
            fail_list.append(
                {
                    "file_name": file_name,
                    "error_code": int(ErrorCode.PARSE_FAILED),
                    "error_message": "文档解析失败，请检查文件后重试",
                }
            )
    return {"total": len(files), "success_list": success_list, "fail_list": fail_list}


def _doc_item(doc: KnowledgeDoc) -> dict:
    return {
        "id": doc.id,
        "title": doc.title,
        "file_name": doc.file_name,
        "file_ext": doc.file_ext,
        "file_size": doc.file_size,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "page_count": doc.page_count,
        "error_message": doc.error_message,
        "created_at": fmt_dt(doc.created_at),
    }


def list_documents(
    db: Session,
    current: CurrentUser,
    *,
    class_id: int,
    status: int | None,
    page: int,
    page_size: int,
) -> dict:
    require_owned_class(db, class_id, current.user_id)
    repo = KnowledgeDocRepository(db)
    total = repo.count_by_class(class_id, status=status)
    rows = repo.list_by_class(
        class_id, status=status, offset=(page - 1) * page_size, limit=page_size
    )
    return page_data([_doc_item(doc) for doc in rows], total, page, page_size)


def get_document(db: Session, current: CurrentUser, doc_id: int) -> dict:
    doc = _require_document(db, current, doc_id)
    return {
        "id": doc.id,
        "class_id": doc.class_id,
        "course_name": doc.course_name,
        "title": doc.title,
        "file_name": doc.file_name,
        "file_ext": doc.file_ext,
        "file_size": doc.file_size,
        "status": doc.status,
        "error_code": doc.error_code,
        "error_message": doc.error_message,
        "page_count": doc.page_count,
        "chunk_count": doc.chunk_count,
        "created_at": fmt_dt(doc.created_at),
    }


def _require_document(db: Session, current: CurrentUser, doc_id: int) -> KnowledgeDoc:
    doc = KnowledgeDocRepository(db).get_by_id(doc_id)
    if doc is None:
        raise AppException(ErrorCode.NOT_FOUND, "文档不存在")
    require_owned_class(db, doc.class_id, current.user_id)
    return doc


def list_chunks(
    db: Session,
    current: CurrentUser,
    doc_id: int,
    *,
    page: int,
    page_size: int,
) -> dict:
    doc = _require_document(db, current, doc_id)
    repo = KnowledgeChunkRepository(db)
    total = repo.count_by_doc(doc.id, doc.class_id)
    rows = repo.list_by_doc(
        doc.id, doc.class_id, offset=(page - 1) * page_size, limit=page_size
    )
    items = [
        {
            "id": chunk.id,
            "chunk_index": chunk.chunk_index,
            "doc_name": chunk.doc_name,
            "chapter_title": chunk.chapter_title,
            "page_no": chunk.page_no,
            "char_count": chunk.char_count,
            "content": chunk.content,
        }
        for chunk in rows
    ]
    return page_data(items, total, page, page_size)


def delete_document(db: Session, current: CurrentUser, doc_id: int) -> None:
    doc = _require_document(db, current, doc_id)
    relative_path = doc.file_path
    class_id = doc.class_id
    KnowledgeChunkRepository(db).delete_by_doc(doc.id, class_id)
    db.delete(doc)
    db.commit()
    try:
        get_storage().delete(relative_path)
    except Exception as exc:  # noqa: BLE001 - 文件删除失败不回滚
        logger.warning("删除磁盘文件失败 {}: {}", relative_path, exc)
    if get_settings().vector_index_enabled:
        logger.info("VECTOR_INDEX_ENABLED=true，M1 不执行 Qdrant 删除 doc_id={}", doc_id)
