"""生成 QQ 演示数据：docs/demo/seed_qq_demo_v1.2.{mysql,sqlite}.sql。

同一个 Python 数据源生成两种方言，避免两份 SQL 漂移。
默认只写 SQL 文件；--build-sqlite 用于本地验证时创建独立 demo.db（绝不碰 contract.db）。
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs" / "demo"
HASH = "$2b$12$1//BMgPXB0fP.YWCDiXz7.XdEE9YF2gokB0WQV6cNGPi3HuKp55la"
NOW = ("NOW()", "datetime('now','localtime')")
DATE = ("CURDATE()", "date('now','localtime')")


class Raw:
    def __init__(self, mysql: str, sqlite: str):
        self.mysql = mysql
        self.sqlite = sqlite


def now() -> Raw:
    return Raw("NOW()", "datetime('now','localtime')")


def days_ago(n: int, *, date_only: bool = False) -> Raw:
    if date_only:
        return Raw(f"DATE_SUB(CURDATE(), INTERVAL {n} DAY)", f"date('now','-{n} days')")
    return Raw(f"DATE_SUB(NOW(), INTERVAL {n} DAY)", f"datetime('now','-{n} days')")


def minutes_from_now(n: int) -> Raw:
    return Raw(f"DATE_ADD(NOW(), INTERVAL {n} MINUTE)", f"datetime('now','+{n} minutes')")


def lit(value, dialect: str) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, Raw):
        return value.mysql if dialect == "mysql" else value.sqlite
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("\\", "\\\\").replace("'", "''")
    return f"'{text}'"


def insert(table: str, columns: list[str], rows: list[list], dialect: str) -> str:
    verb = "INSERT IGNORE" if dialect == "mysql" else "INSERT OR IGNORE"
    values = ",\n".join(
        "(" + ", ".join(lit(value, dialect) for value in row) + ")" for row in rows
    )
    return f"{verb} INTO `{table}` ({', '.join(f'`{c}`' for c in columns)}) VALUES\n{values};\n"


STUDENTS = [
    "李小明", "张雨欣", "王浩然", "陈思远", "刘一诺",
    "赵子涵", "周佳怡", "吴俊杰", "郑雅文", "孙铭泽",
]

QUESTIONS = [
    ("single", "TCP 属于 OSI 模型的哪一层？", [{"key": "A", "text": "应用层"}, {"key": "B", "text": "传输层"}, {"key": "C", "text": "网络层"}, {"key": "D", "text": "数据链路层"}], "B", "TCP 提供端到端可靠传输，位于传输层。", "OSI 分层", "easy"),
    ("single", "UDP 的主要特点是？", [{"key": "A", "text": "可靠、面向连接"}, {"key": "B", "text": "无连接、开销小"}, {"key": "C", "text": "必须重传"}, {"key": "D", "text": "保证顺序"}], "B", "UDP 无连接、不保证可靠与顺序，开销小。", "UDP", "easy"),
    ("single", "TCP 三次握手中，客户端第一个报文段的标志位是？", [{"key": "A", "text": "SYN=1, ACK=0"}, {"key": "B", "text": "SYN=1, ACK=1"}, {"key": "C", "text": "FIN=1"}, {"key": "D", "text": "RST=1"}], "A", "第一个报文为 SYN，尚未确认对方。", "三次握手", "medium"),
    ("single", "TCP 三次握手的第二个报文段通常包含？", [{"key": "A", "text": "SYN=1, ACK=1"}, {"key": "B", "text": "只有 ACK"}, {"key": "C", "text": "FIN=1"}, {"key": "D", "text": "PSH=1"}], "A", "服务器回复 SYN+ACK，确认客户端并同步自己的序号。", "三次握手", "medium"),
    ("judge", "TCP 提供可靠、面向连接的字节流服务。", None, True, "TCP 通过序号、确认和重传提供可靠传输。", "TCP", "easy"),
    ("judge", "UDP 提供可靠传输并保证数据按序到达。", None, False, "UDP 不保证可靠性和顺序。", "UDP", "easy"),
    ("judge", "OSI 模型共有七层。", None, True, "OSI 分为物理、数据链路、网络、传输、会话、表示、应用七层。", "OSI 分层", "easy"),
    ("judge", "IP 协议位于传输层。", None, False, "IP 位于网络层。", "OSI 分层", "easy"),
    ("single", "数据封装过程中，应用层数据最先被封装为？", [{"key": "A", "text": "帧"}, {"key": "B", "text": "段/数据报"}, {"key": "C", "text": "包"}, {"key": "D", "text": "比特"}], "B", "传输层把应用数据封装为段（TCP）或数据报（UDP）。", "封装", "medium"),
    ("single", "交换机主要根据什么转发数据帧？", [{"key": "A", "text": "IP 地址"}, {"key": "B", "text": "MAC 地址"}, {"key": "C", "text": "端口号"}, {"key": "D", "text": "域名"}], "B", "二层交换机根据 MAC 地址表转发帧。", "数据链路层", "medium"),
    ("single", "路由器主要工作在哪一层？", [{"key": "A", "text": "物理层"}, {"key": "B", "text": "数据链路层"}, {"key": "C", "text": "网络层"}, {"key": "D", "text": "应用层"}], "C", "路由器根据 IP 地址在网络层转发分组。", "网络层", "easy"),
    ("single", "TCP 连接释放通常需要几次挥手？", [{"key": "A", "text": "2 次"}, {"key": "B", "text": "3 次"}, {"key": "C", "text": "4 次"}, {"key": "D", "text": "5 次"}], "C", "TCP 连接释放通常为四次挥手。", "TCP", "medium"),
    ("judge", "同一子网内的主机通信一定经过路由器。", None, False, "同一子网内可直接通过 ARP/二层通信，不一定经过路由器。", "网络层", "medium"),
    ("judge", "DNS 的主要作用是把域名解析为 IP 地址。", None, True, "DNS 提供域名到 IP 的解析。", "应用层", "easy"),
    ("blank", "OSI 参考模型中，负责端到端可靠传输的是____层。", None, ["传输"], "传输层负责端到端通信。", "OSI 分层", "easy"),
    ("blank", "TCP 三次握手中第一个报文段的标志位是____。", None, ["SYN"], "SYN 表示同步序号。", "三次握手", "medium"),
    ("multiple", "以下哪些协议位于应用层？", [{"key": "A", "text": "HTTP"}, {"key": "B", "text": "DNS"}, {"key": "C", "text": "TCP"}, {"key": "D", "text": "SMTP"}], ["A", "B", "D"], "TCP 属于传输层；HTTP/DNS/SMTP 属于应用层。", "应用层", "medium"),
    ("multiple", "以下哪些属于 TCP 的特性？", [{"key": "A", "text": "面向连接"}, {"key": "B", "text": "可靠传输"}, {"key": "C", "text": "无连接"}, {"key": "D", "text": "流量控制"}], ["A", "B", "D"], "TCP 面向连接、可靠、有流量控制；无连接是 UDP。", "TCP", "medium"),
    ("single", "ARP 协议的作用是？", [{"key": "A", "text": "域名解析"}, {"key": "B", "text": "IP 地址解析为 MAC 地址"}, {"key": "C", "text": "分配 IP 地址"}, {"key": "D", "text": "路由选择"}], "B", "ARP 把 IPv4 地址解析为链路层 MAC 地址。", "数据链路层", "medium"),
    ("judge", "网络层的主要设备包括路由器和三层交换机。", None, True, "两者都可执行三层转发。", "网络层", "medium"),
]

OFFSETS = [1, 2, 3, 5, 7, 10, 14, 21, 28, 35, 60, 90, 120, 150, 180, 210, 240, 270, 300, 350]


def q_json(q):
    qtype, stem, options, answer, analysis, tag, difficulty = q
    import json

    return [
        qtype,
        stem,
        json.dumps(options, ensure_ascii=False) if options is not None else None,
        json.dumps(answer, ensure_ascii=False),
        analysis,
        tag,
        difficulty,
    ]


def generate(dialect: str) -> str:
    lines: list[str] = [
        "-- 青芽 SproutLearn QQ 演示数据 v1.2",
        "-- 仅用于独立 demo 库；固定 ID + INSERT IGNORE，不含全局 DELETE/TRUNCATE。",
        "-- 由 backend/scripts/generate_qq_demo_seed.py 生成，请勿手改。",
        "SET NAMES utf8mb4;" if dialect == "mysql" else "PRAGMA foreign_keys=ON;",
        "START TRANSACTION;" if dialect == "mysql" else "BEGIN TRANSACTION;",
        "",
    ]

    def add(table, columns, rows):
        if rows:
            lines.append(insert(table, columns, rows, dialect))

    add("teacher", ["id", "account", "password_hash", "name", "email", "phone", "status", "last_login_at", "created_at", "updated_at"], [[9001, "demo.teacher@school.edu.cn", HASH, "王老师", "demo.teacher@school.edu.cn", None, 1, now(), now(), now()]])
    add("class", ["id", "class_code", "teacher_id", "class_name", "course_name", "status", "created_at", "updated_at"], [[9001, "C26A79", 9001, "计算机网络演示班", "计算机网络", 1, now(), now()]])
    add("class_invite", ["id", "class_id", "code", "status", "expires_at", "created_by", "created_at", "updated_at"], [[9001, 9001, "DEMO26", 1, None, 9001, now(), now()]])
    add("student", ["id", "class_id", "student_no", "name", "password_hash", "xp_total", "level", "status", "last_login_at", "streak_days", "last_login_date", "created_at", "updated_at"], [[9001 + i, 9001, f"202601{i+1:02d}", name, HASH, 400, 3, 1, days_ago(1), 3, days_ago(1, date_only=True), now(), now()] for i, name in enumerate(STUDENTS)])

    # global configs
    add("xp_config", ["code", "name", "base_xp", "enabled"], [
        ["daily_login", "每日首次登录", 10, 1], ["homework", "完成作业", 20, 1],
        ["exam", "参加考试", 50, 1], ["practice", "刷题", 1, 1],
        ["wrong_redo", "错题重做", 6, 1], ["streak", "连击", 5, 1],
    ])
    add("difficulty_factor", ["code", "name", "factor"], [["easy", "简单", 1], ["medium", "中等", 2], ["hard", "困难", 3], ["unknown", "未分类", 2]])
    add("login_streak_rule", ["streak_day", "xp"], [[1, 10], [2, 15], [3, 20], [4, 25], [5, 30]])
    add("xp_limit_config", ["code", "value", "unit", "remark"], [["practice_daily_cap", 200, "xp/day", "刷题每日经验封顶"], ["streak_daily_cap", 30, "xp/day", "连击每日经验封顶"], ["min_answer_seconds", 5, "second", "单题作答低于该时长不计经验"]])
    add("level_def", ["level", "title", "min_xp"], [[1, "见习学者", 0], [2, "求知者", 100], [3, "探索者", 250], [4, "精进者", 450], [5, "笃行者", 700], [6, "博闻者", 1000]])
    add("grading_config", ["code", "value", "remark"], [["confidence_threshold", "0.60", "低置信度进入复核"], ["judge_mode_default", "smart", "默认判题模式"]])

    add("question_bank", ["id", "class_id", "name", "description", "created_by", "created_at", "updated_at", "deleted_at"], [[9001, 9001, "计算机网络演示题库", "TCP/IP、OSI、UDP、三次握手、封装", 9001, now(), now(), None]])
    qrows = []
    for i, q in enumerate(QUESTIONS):
        qtype, stem, options, answer, analysis, tag, difficulty = q_json(q)
        qrows.append([9101 + i, 9001, 9001, qtype, stem, options, answer, analysis, tag, difficulty, "published", 9001, None, now(), now()])
    add("question", ["id", "class_id", "bank_id", "type", "stem", "options_json", "answer_json", "analysis", "knowledge_tag", "difficulty", "status", "created_by", "deleted_at", "created_at", "updated_at"], qrows)

    add("knowledge_doc", ["id", "class_id", "course_name", "title", "file_name", "file_ext", "file_size", "file_path", "file_hash", "status", "error_code", "error_message", "page_count", "chunk_count", "created_by", "created_at", "updated_at"], [
        [9401, 9001, "计算机网络", "TCP/UDP 与三次握手", "tcp-udp.md", ".md", 4096, "demo/tcp-udp.md", "a" * 64, 2, None, None, 1, 2, 9001, now(), now()],
        [9402, 9001, "计算机网络", "OSI 分层与封装", "osi.md", ".md", 4096, "demo/osi.md", "b" * 64, 2, None, None, 1, 2, 9001, now(), now()],
    ])
    add("knowledge_chunk", ["id", "doc_id", "class_id", "doc_name", "chunk_index", "content", "char_count", "chapter_title", "page_no", "vector_id", "created_at"], [
        [9501, 9401, 9001, "TCP/UDP 与三次握手", 0, "TCP 面向连接、可靠，通过序号、确认和重传保证数据；UDP 无连接、开销小，不保证可靠与顺序。", 58, "传输层", 1, None, now()],
        [9502, 9401, 9001, "TCP/UDP 与三次握手", 1, "TCP 三次握手：客户端发送 SYN；服务器回复 SYN+ACK；客户端再发送 ACK。三次握手建立可靠连接。", 55, "三次握手", 2, None, now()],
        [9503, 9402, 9001, "OSI 分层与封装", 0, "OSI 七层从下到上为物理层、数据链路层、网络层、传输层、会话层、表示层、应用层。", 49, "OSI", 1, None, now()],
        [9504, 9402, 9001, "OSI 分层与封装", 1, "封装时应用层数据在传输层变为段/数据报，在网络层变为分组，在数据链路层变为帧，最后以比特传输。", 54, "封装", 2, None, now()],
    ])

    # Paper 1 homework, 10 questions; Paper 2 practice, 20 questions
    add("paper", ["id", "class_id", "title", "mode", "kind", "blank_mode", "duration_minutes", "shuffle", "question_count", "total_score", "status", "created_by", "published_at", "due_at", "created_at"], [
        [9201, 9001, "计算机网络基础·第一次作业", "fixed", "homework", "smart", 0, 0, 10, 10, "published", 9001, days_ago(1), minutes_from_now(90), days_ago(2)],
        [9202, 9001, "TCP/IP 随堂练习", "fixed", "practice", "smart", 0, 0, 20, 20, "published", 9001, days_ago(20), None, days_ago(21)],
    ])
    pq = []
    for i, q in enumerate(QUESTIONS[:10]):
        pq.append([9211 + i, 9201, 9101 + i, i + 1, 1.0])
    for i, q in enumerate(QUESTIONS):
        pq.append([9231 + i, 9202, 9101 + i, i + 1, 1.0])
    add("paper_question", ["id", "paper_id", "question_id", "seq", "score"], pq)

    # Homework attempts: 4 submitted/graded, 2 doing, 4 absent
    attempts = []
    for idx in range(4):
        sid = 9001 + idx
        status = "submitted" if idx < 2 else "graded"
        score = 8.0 if idx < 2 else 9.0
        attempts.append([9301 + idx, 9201, 9001, sid, days_ago(3 - idx), None, days_ago(2), status, score, 10.0])
    for idx in range(2):
        sid = 9005 + idx
        attempts.append([9305 + idx, 9201, 9001, sid, days_ago(1), None, None, "doing", 0, 10.0])
    # practice attempts all 10 for activity
    for idx in range(10):
        attempts.append([9401 + idx, 9202, 9001, 9001 + idx, days_ago(20), None, days_ago(1), "graded", 16.0, 20.0])
    add("attempt", ["id", "paper_id", "class_id", "student_id", "started_at", "deadline_at", "submitted_at", "status", "total_score", "full_score"], attempts)

    answers = []
    aid = 9601
    # 4 homework attempts answered 10 questions
    for attempt_index in range(4):
        for qi in range(10):
            correct = qi < (8 if attempt_index < 2 else 9)
            answers.append([aid, 9301 + attempt_index, 9101 + qi, json_answer(QUESTIONS[qi], correct), 1.0 if correct else 0.0, 1 if correct else 0, "demo", 1.0, 0, '{"source":"demo"}', days_ago(2)])
            aid += 1
    # 2 doing attempts: partial answers
    for attempt_index in range(2):
        for qi in range(2):
            answers.append([aid, 9305 + attempt_index, 9101 + qi, json_answer(QUESTIONS[qi], True), 1.0, 1, "demo", 1.0, 0, '{"source":"demo"}', days_ago(1)])
            aid += 1
    # practice activity: 20 answers per student, updated_at across 20 sparse days
    practice_answer_ids = {}
    for sidx, sid in enumerate(range(9001, 9011)):
        for qi, offset in enumerate(OFFSETS):
            rid = 9801 + sidx * 20 + qi
            practice_answer_ids[(sid, qi)] = rid
            answers.append([rid, 9401 + sidx, 9101 + qi, json_answer(QUESTIONS[qi], qi % 5 != 0), 1.0 if qi % 5 != 0 else 0.0, 1 if qi % 5 != 0 else 0, "demo", 1.0, 0, '{"source":"demo"}', days_ago(offset)])
    add("answer_record", ["id", "attempt_id", "question_id", "raw_answer_json", "score", "is_correct", "engine", "confidence", "needs_review", "detail_json", "updated_at"], answers)

    # review one homework answer
    add("review", ["id", "attempt_id", "answer_record_id", "teacher_id", "old_score", "new_score", "comment", "created_at"], [[9701, 9304, 9631, 9001, 0.0, 1.0, "演示复核：步骤正确，补上关键词。", days_ago(1)]])

    # daily xp + ledger; 20 sparse days per student
    daily = []
    ledger = []
    did = 9901
    lid = 9951
    for sidx, sid in enumerate(range(9001, 9011)):
        for qi, offset in enumerate(OFFSETS):
            daily.append([did, sid, days_ago(offset, date_only=True), 0, 20, 0, 0, 20, 0])
            did += 1
            ledger.append([lid, sid, "practice", "answer_record", practice_answer_ids[(sid, qi)], 20, "演示练习", days_ago(offset)])
            lid += 1
    add("student_daily_xp", ["id", "student_id", "stat_date", "login_xp", "practice_xp", "streak_xp", "submission_xp", "total_xp", "login_awarded"], daily)
    add("xp_ledger", ["id", "student_id", "source", "ref_type", "ref_id", "xp", "note", "created_at"], ledger)

    # notifications: new homework + review
    notifs = []
    nid = 10001
    for sid in range(9001, 9011):
        notifs.append([nid, "student", sid, 9001, "paper_published", "新作业：计算机网络基础·第一次作业", "开始：昨天；截止：今天+90 分钟", "/student/papers/9201", '{"paper_id":9201}', 0, None, days_ago(1)])
        nid += 1
    for sid in range(9001, 9005):
        notifs.append([nid, "student", sid, 9001, "grading_reviewed", "成绩已复核：计算机网络基础·第一次作业", "教师已复核，总分 9", "/student/attempts/9304/result", '{"attempt_id":9304}', 0, None, days_ago(1)])
        nid += 1
    add("notification", ["id", "recipient_role", "recipient_id", "class_id", "type", "title", "body", "target_path", "payload_json", "is_read", "read_at", "created_at"], notifs)

    add("class_bot_config", ["id", "class_id", "app_id", "callback_url", "enabled", "group_openid", "teacher_openid", "teacher_bound_at", "binding_enabled", "notify_assignment", "notify_due_soon", "mention_missing", "allow_query_assignments", "allow_query_scores", "bot_chat_mode", "bot_chat_enabled", "bot_chat_max_chars", "last_check_at", "last_check_status", "created_by", "created_at", "updated_at"], [
        [1001, 9001, "env", None, 1, None, None, None, 1, 1, 1, 1, 1, 1, "balanced", 1, 600, None, "never", 9001, now(), now()]
    ])

    lines.append("COMMIT;" if dialect == "mysql" else "COMMIT;")
    return "\n".join(lines)


def json_answer(q, correct: bool):
    qtype, stem, options, answer, analysis, tag, difficulty = q
    if qtype == "judge":
        val = answer if correct else not answer
    elif qtype == "single":
        val = answer if correct else next((o["key"] for o in options if o["key"] != answer), answer)
    elif qtype == "multiple":
        val = answer if correct else ["A"]
    else:
        val = answer if correct else ["错误答案"]
    import json
    return json.dumps(val, ensure_ascii=False)


def build_sqlite(path: Path) -> None:
    # 延迟导入，避免默认生成 SQL 时连接数据库
    import sys
    backend = ROOT / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    from sqlalchemy import create_engine
    from app.models import Base

    if path.exists():
        path.unlink()
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    engine.dispose()
    sqlite3.connect(path).executescript(generate("sqlite"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-sqlite", type=Path, default=None)
    args = parser.parse_args()
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "seed_qq_demo_v1.2.mysql.sql").write_text(generate("mysql"), encoding="utf-8")
    (DOCS / "seed_qq_demo_v1.2.sqlite.sql").write_text(generate("sqlite"), encoding="utf-8")
    print("generated mysql/sqlite seed")
    if args.build_sqlite:
        build_sqlite(args.build_sqlite)
        print(f"built sqlite demo: {args.build_sqlite}")


if __name__ == "__main__":
    main()
