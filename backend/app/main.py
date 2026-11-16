"""FastAPI 入口：路由注册、CORS、中间件、统一异常处理、健康检查。"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.exceptions import AppException, ErrorCode
from app.logging_config import setup_logging
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.request_log import RequestLogMiddleware
from app.routers import attempts, auth, banks, binding, bot, classes, health, knowledge, notifications, papers, questions, workbench
from app.services.llm.registry import validate_chain
from app.utils.response import fail

settings = get_settings()


def create_app() -> FastAPI:
    setup_logging()
    # M2A：未知 LLM_CHAIN 标识在启动期直接失败（只构造，不发网络请求）
    validate_chain(settings)
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="青芽 SproutLearn M1/M2A/M2B 后端 API（M1 字段与契约 §7 一致）",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[settings.request_id_header],
    )
    # 注意顺序：后添加的中间件在最外层，RequestId 必须包住 RequestLog
    application.add_middleware(RequestLogMiddleware)
    application.add_middleware(RequestIdMiddleware)

    application.include_router(auth.router, prefix="/api/v1")
    application.include_router(classes.router, prefix="/api/v1")
    application.include_router(knowledge.router, prefix="/api/v1")
    application.include_router(binding.router, prefix="/api/v1")
    application.include_router(banks.router, prefix="/api/v1")
    application.include_router(questions.router, prefix="/api/v1")
    application.include_router(papers.router, prefix="/api/v1")
    application.include_router(attempts.router, prefix="/api/v1")
    application.include_router(workbench.router, prefix="/api/v1")
    application.include_router(bot.router, prefix="/api/v1")
    application.include_router(notifications.router, prefix="/api/v1")
    application.include_router(health.router)
    # 派工词要求 /api/v1/health；契约 API-20 为 /health。别名不进入 OpenAPI，保持 20 接口不变。
    application.add_api_route(
        "/api/v1/health", health.health, methods=["GET"], include_in_schema=False
    )

    _register_exception_handlers(application)
    logger.info("应用启动 {}", settings.summary())
    return application


def _register_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.http_status,
            content=fail(exc.code, exc.message, exc.data),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=fail(
                int(ErrorCode.VALIDATION_ERROR),
                "参数校验失败",
                jsonable_encoder(exc.errors()),
            ),
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        status_map = {
            401: (ErrorCode.UNAUTHORIZED, "未登录"),
            403: (ErrorCode.ROLE_FORBIDDEN, "角色无权限"),
            404: (ErrorCode.NOT_FOUND, "资源不存在"),
            405: (ErrorCode.VALIDATION_ERROR, "请求方法不允许"),
            429: (ErrorCode.RATE_LIMITED, "请求过于频繁，请稍后再试"),
        }
        code, message = status_map.get(
            exc.status_code,
            (ErrorCode.VALIDATION_ERROR, str(exc.detail) if exc.detail else "请求失败"),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=fail(int(code), message),
        )

    @application.exception_handler(Exception)
    async def global_handler(request: Request, exc: Exception):
        logger.exception("未捕获异常 {} {}", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=fail(int(ErrorCode.INTERNAL_ERROR), "服务器内部错误"),
        )


app = create_app()
