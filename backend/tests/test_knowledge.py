"""知识库冒烟测试：AC-10/11/12/13/14/15，含扫描件 42201 与切片 doc_name。"""

from __future__ import annotations

from app.config import get_settings
from tests.conftest import auth
from tests.pdf_utils import make_pdf

TEXT_PDF = make_pdf("Chapter 1 TCP\nTransmission Control Protocol provides reliable delivery.")
SCAN_PDF = make_pdf(None)
TXT_CONTENT = (
    "第一章 计算机网络概述\n"
    "计算机网络是把地理位置不同的计算机连接起来，实现资源共享和信息传递的系统。\n"
    "本章介绍网络分层、协议与常见设备。"
)


def _upload(client, token: str, class_id: int, files: list[tuple[str, bytes, str]]):
    return client.post(
        "/api/v1/knowledge/documents",
        headers=auth(token),
        data={"class_id": str(class_id), "course_name": "计算机网络"},
        files=[("files", (name, content, mime)) for name, content, mime in files],
    )


def test_upload_partial_success_and_scan_pdf(client, klass, teacher_token):
    response = _upload(
        client,
        teacher_token,
        klass["id"],
        [
            ("第3章 TCP.pdf", TEXT_PDF, "application/pdf"),
            ("第1章 概述.txt", TXT_CONTENT.encode("utf-8"), "text/plain"),
            ("扫描版讲义.pdf", SCAN_PDF, "application/pdf"),
        ],
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["total"] == 3
    assert len(data["success_list"]) == 2
    assert len(data["fail_list"]) == 1
    assert data["fail_list"][0]["error_code"] == 42201
    assert isinstance(data["fail_list"][0]["error_code"], int)

    pdf_success = next(item for item in data["success_list"] if item["file_name"].endswith(".pdf"))
    txt_success = next(item for item in data["success_list"] if item["file_name"].endswith(".txt"))
    assert pdf_success["status"] == 2
    assert pdf_success["chunk_count"] > 0
    assert pdf_success["page_count"] == 1

    pdf_detail = client.get(
        f"/api/v1/knowledge/documents/{pdf_success['doc_id']}", headers=auth(teacher_token)
    )
    assert pdf_detail.status_code == 200
    pdf_title = pdf_detail.json()["data"]["title"]

    pdf_chunks = client.get(
        f"/api/v1/knowledge/documents/{pdf_success['doc_id']}/chunks",
        headers=auth(teacher_token),
    )
    assert pdf_chunks.status_code == 200
    pdf_chunk_data = pdf_chunks.json()["data"]
    assert pdf_chunk_data["total"] == pdf_success["chunk_count"]
    first_pdf_chunk = pdf_chunk_data["list"][0]
    assert first_pdf_chunk["doc_name"] == pdf_title
    assert first_pdf_chunk["page_no"] == 1
    assert first_pdf_chunk["chapter_title"]
    assert first_pdf_chunk["char_count"] == len(first_pdf_chunk["content"])

    txt_chunks = client.get(
        f"/api/v1/knowledge/documents/{txt_success['doc_id']}/chunks",
        headers=auth(teacher_token),
    )
    assert txt_chunks.status_code == 200
    for chunk in txt_chunks.json()["data"]["list"]:
        assert chunk["page_no"] is None
        assert chunk["char_count"] == len(chunk["content"])
        assert chunk["doc_name"]


def test_upload_ext_and_size_guard(client, klass, teacher_token, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_max_mb", 1)
    large = b"x" * (1024 * 1024 + 10)
    response = _upload(
        client,
        teacher_token,
        klass["id"],
        [
            ("恶意.exe", b"MZ", "application/octet-stream"),
            ("超大.txt", large, "text/plain"),
            ("正常.txt", "正常内容".encode("utf-8"), "text/plain"),
        ],
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert len(data["success_list"]) == 1
    codes = {item["error_code"] for item in data["fail_list"]}
    assert codes == {41301, 41501}

    duplicate = _upload(
        client,
        teacher_token,
        klass["id"],
        [("正常.txt", "正常内容".encode("utf-8"), "text/plain")],
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["data"]["success_list"] == []
    assert duplicate.json()["data"]["fail_list"][0]["error_code"] == 40906

    monkeypatch.setattr(settings, "max_files_per_request", 2)
    too_many = _upload(
        client,
        teacher_token,
        klass["id"],
        [
            ("a.txt", b"a", "text/plain"),
            ("b.txt", b"b", "text/plain"),
            ("c.txt", b"c", "text/plain"),
        ],
    )
    assert too_many.status_code == 422
    assert too_many.json()["code"] == 40001

    monkeypatch.setattr(settings, "max_files_per_request", 20)
    monkeypatch.setattr(settings, "max_total_upload_mb", 1)
    too_large_total = _upload(
        client,
        teacher_token,
        klass["id"],
        [
            ("t1.txt", b"a" * 600_000, "text/plain"),
            ("t2.txt", b"b" * 600_000, "text/plain"),
        ],
    )
    assert too_large_total.status_code == 422
    assert too_large_total.json()["code"] == 40001
