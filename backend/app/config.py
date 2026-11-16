"""应用配置：统一从环境变量 / .env 读取，禁止在业务代码写死阈值。"""

from functools import lru_cache
from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pydantic Settings：字段名与 .env 变量一一对应（大小写不敏感）。"""

    model_config = SettingsConfigDict(
        # 本地从 backend/ 启动时读取仓库根 .env；容器内由 compose env_file 注入
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- 应用 ----------
    app_env: str = "dev"
    app_name: str = "青芽 SproutLearn"
    app_version: str = "0.1.0"
    app_port: int = 8000
    log_level: str = "INFO"
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    request_id_header: str = "X-Request-Id"
    slow_request_ms: int

    # ---------- 安全 ----------
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_minutes: int
    session_idle_minutes: int
    bcrypt_rounds: int

    # ---------- MySQL ----------
    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_user: str = "sproutlearn"
    mysql_password: str = ""
    mysql_database: str = "sproutlearn"
    mysql_pool_size: int = 10
    mysql_pool_max_overflow: int = 20

    # ---------- Redis ----------
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0

    # ---------- Qdrant ----------
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""
    qdrant_collection: str = "kb_chunks"
    vector_dim: int = 1024
    vector_distance: str = "Cosine"
    vector_index_enabled: bool = False

    # ---------- 上传与解析 ----------
    upload_dir: str = "/data/uploads"
    upload_max_mb: int
    max_total_upload_mb: int
    upload_allowed_ext: str
    pdf_min_text_chars: int
    parser_timeout_seconds: int
    chunk_size: int
    chunk_overlap: int
    max_files_per_request: int

    # ---------- 编码生成 ----------
    class_code_length: int
    max_classes_per_teacher: int
    text_field_max_len: int
    invite_code_length: int
    invite_code_ttl_minutes: int
    code_retry_limit: int
    bind_code_length: int
    bind_code_ttl_seconds: int
    bind_max_attempts: int
    bind_attempt_ttl_seconds: int

    # ---------- 限流 ----------
    rate_limit_login: str
    rate_limit_join: str
    rate_limit_invite_reset: str
    rate_limit_upload: str

    # ---------- 机器人（M2+ 回调鉴权；M3.4 官方机器人配置） ----------
    bot_shared_secret: str = ""
    qq_bot_app_id: str = ""
    qq_bot_app_secret: str = ""
    qq_bot_enabled: bool = False
    qq_bot_gateway_url: str = ""
    qq_bot_explain_timeout_seconds: int = 8

    # ---------- 模型路由（M2A） ----------
    llm_chain: str = "amd,zhipu,deepseek"
    llm_timeout_seconds: int = 15
    llm_explain_timeout_seconds: int = 45
    llm_max_retries: int = 1
    amd_base_url: str = "https://developer.amd.com.cn/radeon/api/v1"
    amd_api_key: str = ""
    amd_model: str = "DeepSeek-V4-Flash"
    zhipu_base_url: str = "https://open.bigmodel.cn/api/coding/paas/v4"
    zhipu_api_key: str = ""
    zhipu_model: str = "glm-4.5-flash"
    zhipu_model_fallback: str = "glm-4.7-flash"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_model: str = "DeepSeek-V4.1-Flash"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str = ""

    # ---------- Jev 判分内核（M2A，独立链路） ----------
    jev_enabled: bool = True
    jev_base_url: str = "https://jev.showapi.com"
    jev_gateway_url: str = "https://route.showapi.com/3627-1"
    jev_appkey: str = ""
    jev_model: str = "JevK5-V0.3"
    jev_timeout_seconds: int = 8
    jev_fallback_to_llm: bool = True

    # ---------- 兼容 M1 旧变量（新代码不读取） ----------
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""

    # ---------- 分页 ----------
    pagination_default_size: int
    pagination_max_size: int

    # ---------- M2B 题库/作答 ----------
    question_import_max_mb: int = 10
    question_import_max_rows: int = 500
    question_import_token_ttl_seconds: int = 1800
    grading_concurrency: int = 5

    # ---------- 其他 ----------
    tz: str = "Asia/Shanghai"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"

    @field_validator("upload_allowed_ext")
    @classmethod
    def _normalize_ext(cls, value: str) -> str:
        return ",".join(item.strip().lower().lstrip(".") for item in value.split(",") if item.strip())

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS 白名单（去空、去重、保序）。"""
        return list(dict.fromkeys(item.strip() for item in self.cors_origins.split(",") if item.strip()))

    @property
    def allowed_ext_set(self) -> set[str]:
        """上传白名单集合（小写、无点）。"""
        return {item for item in self.upload_allowed_ext.split(",") if item}

    @property
    def llm_chain_list(self) -> list[str]:
        """LLM_CHAIN 解析为去空、去重、保序的厂商标识列表。"""
        return list(dict.fromkeys(item.strip().lower() for item in self.llm_chain.split(",") if item.strip()))

    @property
    def max_upload_bytes(self) -> int:
        return self.upload_max_mb * 1024 * 1024

    @property
    def max_total_upload_bytes(self) -> int:
        return self.max_total_upload_mb * 1024 * 1024

    @property
    def access_token_seconds(self) -> int:
        return int(timedelta(minutes=self.access_token_minutes).total_seconds())

    @property
    def session_idle_seconds(self) -> int:
        return int(timedelta(minutes=self.session_idle_minutes).total_seconds())

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.tz)

    @property
    def database_url(self) -> str:
        """MySQL 连接串；用户/密码做 URL 转义，避免特殊字符破坏连接。"""
        user = quote_plus(self.mysql_user)
        password = quote_plus(self.mysql_password)
        return (
            f"mysql+pymysql://{user}:{password}@{self.mysql_host}:{self.mysql_port}/"
            f"{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def upload_root(self) -> Path:
        return Path(self.upload_dir).expanduser()

    def summary(self) -> dict[str, Any]:
        """启动日志用的脱敏配置摘要。"""
        return {
            "app_env": self.app_env,
            "app_version": self.app_version,
            "mysql_host": self.mysql_host,
            "mysql_database": self.mysql_database,
            "redis_host": self.redis_host,
            "qdrant_host": self.qdrant_host,
            "upload_dir": self.upload_dir,
            "vector_index_enabled": self.vector_index_enabled,
            "llm_chain": self.llm_chain_list,
            "jev_enabled": self.jev_enabled,
        }


@lru_cache
def get_settings() -> Settings:
    """全局配置单例；测试可调用 cache_clear() 后重载。"""
    return Settings()
