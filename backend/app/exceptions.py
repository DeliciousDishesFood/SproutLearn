"""统一业务异常与错误码枚举（错误码唯一清单，禁止临时新增）。"""

from enum import IntEnum
from typing import Any


class ErrorCode(IntEnum):
    """第 4.2 章错误码；所有业务异常必须使用这里登记的值。"""

    OK = 0
    VALIDATION_ERROR = 40001
    UNAUTHORIZED = 40101
    SESSION_EXPIRED = 40102
    BAD_CREDENTIALS = 40103
    ROLE_FORBIDDEN = 40301
    CLASS_FORBIDDEN = 40302
    NOT_FOUND = 40401
    STUDENT_NO_EXISTS = 40901
    INVITE_INVALID = 40902
    QQ_ALREADY_BOUND = 40903
    ACCOUNT_EXISTS = 40904
    BIND_CODE_INVALID = 40905
    DOC_DUPLICATE = 40906
    CLASS_LIMIT = 40907
    FILE_TOO_LARGE = 41301
    UNSUPPORTED_FORMAT = 41501
    NO_TEXT_LAYER = 42201
    PARSE_FAILED = 42202
    RATE_LIMITED = 42901
    INTERNAL_ERROR = 50001
    DEPENDENCY_UNAVAILABLE = 50301


# 错误码 → 默认 HTTP 状态码；异常构造未显式传 http_status 时使用
DEFAULT_HTTP_STATUS: dict[int, int] = {
    ErrorCode.OK: 200,
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.SESSION_EXPIRED: 401,
    ErrorCode.BAD_CREDENTIALS: 401,
    ErrorCode.ROLE_FORBIDDEN: 403,
    ErrorCode.CLASS_FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.STUDENT_NO_EXISTS: 409,
    ErrorCode.INVITE_INVALID: 409,
    ErrorCode.QQ_ALREADY_BOUND: 409,
    ErrorCode.ACCOUNT_EXISTS: 409,
    ErrorCode.BIND_CODE_INVALID: 409,
    ErrorCode.DOC_DUPLICATE: 409,
    ErrorCode.CLASS_LIMIT: 409,
    ErrorCode.FILE_TOO_LARGE: 413,
    ErrorCode.UNSUPPORTED_FORMAT: 415,
    ErrorCode.NO_TEXT_LAYER: 422,
    ErrorCode.PARSE_FAILED: 422,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.DEPENDENCY_UNAVAILABLE: 503,
}


class AppException(Exception):
    """业务异常：路由层只抛出该异常，由全局处理器统一转统一响应体。"""

    def __init__(
        self,
        code: int | ErrorCode,
        message: str,
        http_status: int | None = None,
        data: Any = None,
    ) -> None:
        self.code = int(code)
        self.message = message
        self.http_status = http_status or DEFAULT_HTTP_STATUS.get(self.code, 400)
        self.data = data
        super().__init__(message)

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class AppExceptionFactory:
    """按错误码快速构造异常，避免业务层散落 HTTP 状态码。"""

    @staticmethod
    def validation(message: str = "参数校验失败", data: Any = None) -> AppException:
        return AppException(ErrorCode.VALIDATION_ERROR, message, data=data)

    @staticmethod
    def unauthorized(message: str = "未登录") -> AppException:
        return AppException(ErrorCode.UNAUTHORIZED, message)

    @staticmethod
    def session_expired(message: str = "登录已过期") -> AppException:
        return AppException(ErrorCode.SESSION_EXPIRED, message)

    @staticmethod
    def bad_credentials(message: str = "账号或密码错误") -> AppException:
        return AppException(ErrorCode.BAD_CREDENTIALS, message)

    @staticmethod
    def role_forbidden(message: str = "角色无权限") -> AppException:
        return AppException(ErrorCode.ROLE_FORBIDDEN, message)

    @staticmethod
    def class_forbidden(message: str = "无权访问该班级资源") -> AppException:
        return AppException(ErrorCode.CLASS_FORBIDDEN, message)

    @staticmethod
    def not_found(message: str = "资源不存在") -> AppException:
        return AppException(ErrorCode.NOT_FOUND, message)

    @staticmethod
    def rate_limited(message: str = "请求过于频繁，请稍后再试") -> AppException:
        return AppException(ErrorCode.RATE_LIMITED, message)

    @staticmethod
    def dependency_unavailable(message: str = "依赖服务不可用") -> AppException:
        return AppException(ErrorCode.DEPENDENCY_UNAVAILABLE, message)
