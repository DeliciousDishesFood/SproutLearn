"""Redis Key 统一工厂：业务代码禁止手拼 Key（第 6 章）。"""

SESSION = "session:{jti}"
JWT_BLACKLIST = "jwt:blacklist:{jti}"
LOGIN_FAIL = "login:fail:{account}"
RATE_LOGIN_IP = "rate:login:{ip}"
RATE_JOIN_IP = "rate:join:{ip}"
RATE_INVITE_RESET = "rate:invite:reset:{class_id}"
RATE_UPLOAD = "rate:upload:{teacher_id}"
QQ_BIND_CODE = "qq:bind:code:{code}"
QQ_BIND_STUDENT = "qq:bind:student:{student_id}"
QQ_BIND_ATTEMPT = "qq:bind:attempt:{openid}"
PARSE_LOCK = "lock:parse:{doc_id}"
QUESTION_IMPORT = "question:import:{token}"
QUOTE_RANDOM = "quote:random:{type}"


def session_key(jti: str) -> str:
    return SESSION.format(jti=jti)


def jwt_blacklist_key(jti: str) -> str:
    return JWT_BLACKLIST.format(jti=jti)


def login_fail_key(account: str) -> str:
    return LOGIN_FAIL.format(account=account.lower())


def rate_login_key(ip: str) -> str:
    return RATE_LOGIN_IP.format(ip=ip)


def rate_join_key(ip: str) -> str:
    return RATE_JOIN_IP.format(ip=ip)


def rate_invite_reset_key(class_id: int) -> str:
    return RATE_INVITE_RESET.format(class_id=class_id)


def rate_upload_key(teacher_id: int) -> str:
    return RATE_UPLOAD.format(teacher_id=teacher_id)


def qq_bind_code_key(code: str) -> str:
    return QQ_BIND_CODE.format(code=code)


def qq_bind_student_key(student_id: int) -> str:
    return QQ_BIND_STUDENT.format(student_id=student_id)


def qq_bind_attempt_key(openid: str) -> str:
    return QQ_BIND_ATTEMPT.format(openid=openid)


def parse_lock_key(doc_id: int) -> str:
    return PARSE_LOCK.format(doc_id=doc_id)


def question_import_key(token: str) -> str:
    return QUESTION_IMPORT.format(token=token)


def quote_key(quote_type: str) -> str:
    return QUOTE_RANDOM.format(type=quote_type)
