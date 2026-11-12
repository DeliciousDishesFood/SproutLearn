"""pytest 公共 fixture：SQLite 测试库 + fakeredis + 临时上传目录。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# 必须在 import app 之前设置测试环境变量
os.environ.update(
    {
        "APP_ENV": "test",
        "SECRET_KEY": "test-secret-key-please-do-not-use-in-prod",
        "BOT_SHARED_SECRET": "test-bot-secret",
        "BOT_SECRET_KEY": "8VPIzNCL_cmCREPbiX_0wKRZo4nb12shXsFTpjtXh6o=",
        "JWT_ALGORITHM": "HS256",
        "ACCESS_TOKEN_MINUTES": "60",
        "SESSION_IDLE_MINUTES": "30",
        "BCRYPT_ROUNDS": "4",
        "MYSQL_HOST": "127.0.0.1",
        "MYSQL_PORT": "3306",
        "MYSQL_USER": "sproutlearn",
        "MYSQL_PASSWORD": "test",
        "MYSQL_DATABASE": "sproutlearn_test",
        "REDIS_HOST": "127.0.0.1",
        "REDIS_PORT": "6379",
        "REDIS_PASSWORD": "",
        "UPLOAD_MAX_MB": "50",
        "MAX_TOTAL_UPLOAD_MB": "100",
        "UPLOAD_ALLOWED_EXT": "pdf,doc,docx,ppt,pptx,md,txt",
        "MAX_FILES_PER_REQUEST": "20",
        "PDF_MIN_TEXT_CHARS": "10",
        "PARSER_TIMEOUT_SECONDS": "30",
        "CHUNK_SIZE": "80",
        "CHUNK_OVERLAP": "10",
        "CLASS_CODE_LENGTH": "6",
        "MAX_CLASSES_PER_TEACHER": "10",
        "TEXT_FIELD_MAX_LEN": "80",
        "INVITE_CODE_LENGTH": "6",
        "INVITE_CODE_TTL_MINUTES": "0",
        "CODE_RETRY_LIMIT": "3",
        "BIND_CODE_LENGTH": "8",
        "BIND_CODE_TTL_SECONDS": "600",
        "BIND_MAX_ATTEMPTS": "5",
        "BIND_ATTEMPT_TTL_SECONDS": "600",
        "PAGINATION_DEFAULT_SIZE": "10",
        "PAGINATION_MAX_SIZE": "50",
        "SLOW_REQUEST_MS": "1000",
        "RATE_LIMIT_LOGIN": "100/300",
        "RATE_LIMIT_JOIN": "100/3600",
        "RATE_LIMIT_INVITE_RESET": "100/3600",
        "RATE_LIMIT_UPLOAD": "100/3600",
        "LOG_LEVEL": "WARNING",
        # M2A：单测不得触碰真实厂商 key / 真实计费
        "AMD_API_KEY": "",
        "ZHIPU_API_KEY": "",
        "DEEPSEEK_API_KEY": "",
        "OPENROUTER_API_KEY": "",
        "JEV_APPKEY": "",
        "JEV_ENABLED": "false",
    }
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings  # noqa: E402
from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.redis_client import reset_redis_client, set_redis_client  # noqa: E402
from app.strategies.storage import set_storage  # noqa: E402

PASSWORD = "Abc12345"
TEACHER_ACCOUNT = "teacher01@school.edu.cn"
TEACHER_NAME = "张老师"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """每个用例独立 SQLite 文件、独立 fakeredis、独立上传目录。"""
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "bcrypt_rounds", 4)

    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite+pysqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    set_redis_client(fake_redis)
    set_storage(None)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        test_client.fake_redis = fake_redis  # type: ignore[attr-defined]
        test_client.testing_session = testing_session  # type: ignore[attr-defined]
        yield test_client

    app.dependency_overrides.clear()
    reset_redis_client()
    set_storage(None)
    engine.dispose()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_teacher(client: TestClient, account: str = TEACHER_ACCOUNT) -> dict:
    response = client.post(
        "/api/v1/auth/teacher/register",
        json={
            "account": account,
            "name": TEACHER_NAME,
            "password": PASSWORD,
            "email": account,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def create_class(client: TestClient, token: str, name: str = "2026级计算机1班") -> dict:
    response = client.post(
        "/api/v1/classes",
        headers=auth(token),
        json={"class_name": name, "course_name": "计算机网络"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def join_student(
    client: TestClient,
    invite_code: str,
    student_no: str = "20260101",
    name: str = "李同学",
) -> dict:
    response = client.post(
        "/api/v1/classes/join",
        json={
            "invite_code": invite_code,
            "student_no": student_no,
            "name": name,
            "password": PASSWORD,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


@pytest.fixture()
def teacher(client):
    return register_teacher(client)


@pytest.fixture()
def teacher_token(teacher):
    return teacher["token"]


@pytest.fixture()
def klass(client, teacher_token):
    return create_class(client, teacher_token)


@pytest.fixture()
def student(client, klass):
    return join_student(client, klass["invite_code"])
