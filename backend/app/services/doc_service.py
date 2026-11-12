"""M3.3 文档中心：读取 content/docs/manifest.json 与 Markdown 原文。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.exceptions import AppException, ErrorCode

DOCS_DIR = Path(__file__).resolve().parents[2] / "content" / "docs"
MANIFEST = DOCS_DIR / "manifest.json"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def _load_manifest() -> list[dict[str, Any]]:
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [item for item in data if isinstance(item, dict) and item.get("slug")]


def _entry(slug: str) -> dict[str, Any] | None:
    for item in _load_manifest():
        if item.get("slug") == slug:
            return item
    return None


def list_docs() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in _load_manifest():
        slug = str(item["slug"])
        if not SLUG_RE.match(slug):
            continue
        path = DOCS_DIR / f"{slug}.md"
        if not path.is_file():
            continue
        items.append(
            {
                "slug": slug,
                "title": str(item.get("title") or slug),
                "summary": str(item.get("summary") or ""),
                "updated_at": item.get("updated_at"),
            }
        )
    return items


def get_doc(slug: str) -> dict[str, Any]:
    if not SLUG_RE.match(slug):
        raise AppException(ErrorCode.NOT_FOUND, "文档不存在")
    entry = _entry(slug)
    if entry is None:
        raise AppException(ErrorCode.NOT_FOUND, "文档不存在")
    path = (DOCS_DIR / f"{slug}.md").resolve()
    if DOCS_DIR.resolve() not in path.parents or not path.is_file():
        raise AppException(ErrorCode.NOT_FOUND, "文档不存在")
    content = path.read_text(encoding="utf-8")
    return {
        "slug": slug,
        "title": str(entry.get("title") or slug),
        "summary": str(entry.get("summary") or ""),
        "updated_at": entry.get("updated_at"),
        "content": content,
        "markdown": content,
    }
