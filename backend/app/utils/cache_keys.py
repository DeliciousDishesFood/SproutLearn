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
QQ_GROUP_BIND = "qq:group:bind:{code}"
PARSE_LOCK = "lock:parse:{doc_id}"
QUESTION_IMPORT = "question:import:{token}"
QUOTE_RANDOM = "quote:random:{type}"
EXPLAIN = "explain:{question_id}:{updated_at}"
BOT_CHAT = "bot:chat:{openid}"
ASK_SPROUT_COOLDOWN = "ask:sprout:cooldown:{student_id}"
ASK_SPROUT_DAILY = "ask:sprout:daily:{student_id}:{date}"
AI_IMPORT_DAILY = "rate:ai_import:{teacher_id}:{date}"
AI_IMPORT_MINUTE = "rate:ai_import:minute:{teacher_id}:{minute}"


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


def qq_group_bind_key(code: str) -> str:
    return QQ_GROUP_BIND.format(code=code)


def parse_lock_key(doc_id: int) -> str:
    return PARSE_LOCK.format(doc_id=doc_id)


def question_import_key(token: str) -> str:
    return QUESTION_IMPORT.format(token=token)


def quote_key(quote_type: str) -> str:
    return QUOTE_RANDOM.format(type=quote_type)


def explain_key(question_id: int, updated_at: str) -> str:
    return EXPLAIN.format(question_id=question_id, updated_at=updated_at)


def bot_chat_key(openid: str) -> str:
    return BOT_CHAT.format(openid=openid)



def ask_sprout_cooldown_key(student_id: int) -> str:
    return ASK_SPROUT_COOLDOWN.format(student_id=student_id)


def ask_sprout_daily_key(student_id: int, day: str) -> str:
    return ASK_SPROUT_DAILY.format(student_id=student_id, date=day)


def ai_import_daily_key(teacher_id: int, day: str) -> str:
    return AI_IMPORT_DAILY.format(teacher_id=teacher_id, date=day)


def ai_import_minute_key(teacher_id: int, minute: str) -> str:
    return AI_IMPORT_MINUTE.format(teacher_id=teacher_id, minute=minute)
