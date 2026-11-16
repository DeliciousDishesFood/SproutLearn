"""QQ 演示数据只读校验（D1）。

用法：
  python -m scripts.verify_qq_demo --sqlite <demo.db>
  python -m scripts.verify_qq_demo --database-url <sqlalchemy-url>
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

CLASS_CODE = "C26A79"
HOMEWORK_ID = 9201


class Checker:
    def __init__(self, dialect: str, execute):
        self.dialect = dialect
        self.execute = execute

    def scalar(self, sql: str, **params):
        return self.execute(sql, params).scalar()

    def rows(self, sql: str, **params):
        return self.execute(sql, params).fetchall()


def _sqlite_executor(path: Path):
    if not path.exists():
        raise SystemExit(f"SQLite 文件不存在：{path}")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row

    def execute(sql: str, params: dict | None = None):
        class Result:
            def __init__(self, cursor):
                self.cursor = cursor

            def scalar(self):
                row = self.cursor.fetchone()
                return row[0] if row else None

            def fetchall(self):
                return [tuple(row) for row in self.cursor.fetchall()]

        cursor = connection.execute(sql, params or {})
        return Result(cursor)

    return "sqlite", execute, connection.close


def _url_executor(url: str):
    engine = create_engine(url, pool_pre_ping=True)
    connection = engine.connect()

    def execute(sql: str, params: dict | None = None):
        result = connection.execute(text(sql), params or {})

        class Wrapper:
            def scalar(self):
                return result.scalar()

            def fetchall(self):
                return [tuple(row) for row in result.fetchall()]

        return Wrapper()

    return engine.dialect.name, execute, connection.close


def _date_ge(dialect: str, days: int) -> str:
    if dialect == "sqlite":
        return f"date(updated_at) >= date('now','-{days} days')"
    return f"DATE(updated_at) >= DATE_SUB(CURDATE(), INTERVAL {days} DAY)"


def run(dialect: str, execute, close) -> list[str]:
    out: list[str] = []
    checker = Checker(dialect, execute)
    teacher = checker.scalar("SELECT COUNT(*) FROM teacher")
    klass = checker.scalar("SELECT COUNT(*) FROM `class` WHERE class_code=:code", code=CLASS_CODE)
    students = checker.scalar("SELECT COUNT(*) FROM student WHERE class_id=(SELECT id FROM `class` WHERE class_code=:code)", code=CLASS_CODE)
    banks = checker.scalar("SELECT COUNT(*) FROM question_bank WHERE class_id=(SELECT id FROM `class` WHERE class_code=:code)", code=CLASS_CODE)
    questions = checker.scalar("SELECT COUNT(*) FROM question WHERE class_id=(SELECT id FROM `class` WHERE class_code=:code)", code=CLASS_CODE)
    papers = checker.rows("SELECT id,title,kind,status FROM paper WHERE class_id=(SELECT id FROM `class` WHERE class_code=:code) ORDER BY id", code=CLASS_CODE)
    homework_submitted = checker.scalar("SELECT COUNT(*) FROM attempt WHERE paper_id=:pid AND status IN ('submitted','graded')", pid=HOMEWORK_ID)
    homework_doing = checker.scalar("SELECT COUNT(*) FROM attempt WHERE paper_id=:pid AND status='doing'", pid=HOMEWORK_ID)
    homework_attempted = checker.scalar("SELECT COUNT(DISTINCT student_id) FROM attempt WHERE paper_id=:pid", pid=HOMEWORK_ID)
    homework_not_started = max(0, students - homework_attempted)
    docs = checker.scalar("SELECT COUNT(*) FROM knowledge_doc WHERE class_id=(SELECT id FROM `class` WHERE class_code=:code) AND status=2", code=CLASS_CODE)
    chunks = checker.scalar("SELECT COUNT(*) FROM knowledge_chunk WHERE class_id=(SELECT id FROM `class` WHERE class_code=:code)", code=CLASS_CODE)
    searchable = checker.scalar("SELECT COUNT(*) FROM knowledge_chunk WHERE class_id=(SELECT id FROM `class` WHERE class_code=:code) AND (content LIKE '%三次握手%' OR content LIKE '%TCP%')", code=CLASS_CODE)
    activity_days = checker.scalar("SELECT COUNT(DISTINCT date(updated_at)) FROM answer_record")
    last7 = checker.scalar(
        "SELECT COUNT(DISTINCT date(updated_at)) FROM answer_record WHERE " + _date_ge(dialect, 7)
    )
    last30 = checker.scalar(
        "SELECT COUNT(DISTINCT date(updated_at)) FROM answer_record WHERE " + _date_ge(dialect, 30)
    )
    old = checker.scalar(
        "SELECT COUNT(DISTINCT date(updated_at)) FROM answer_record WHERE date(updated_at) <= date('now','-90 days')" if dialect == "sqlite" else
        "SELECT COUNT(DISTINCT DATE(updated_at)) FROM answer_record WHERE DATE(updated_at) <= DATE_SUB(CURDATE(), INTERVAL 90 DAY)"
    )
    bot = checker.rows(
        "SELECT enabled,binding_enabled,notify_assignment,notify_due_soon,mention_missing,"
        "allow_query_assignments,allow_query_scores,bot_chat_enabled,bot_chat_mode,bot_chat_max_chars,"
        "group_openid,teacher_openid,last_check_status,app_id "
        "FROM class_bot_config WHERE class_id=(SELECT id FROM `class` WHERE class_code=:code)",
        code=CLASS_CODE,
    )
    xp_rows = checker.rows(
        "SELECT s.student_no, s.xp_total, s.level, COALESCE(SUM(d.total_xp),0) "
        "FROM student s LEFT JOIN student_daily_xp d ON d.student_id=s.id "
        "WHERE s.class_id=(SELECT id FROM `class` WHERE class_code=:code) GROUP BY s.id ORDER BY s.student_no",
        code=CLASS_CODE,
    )
    out.append(f"teacher={teacher} class={klass} students={students}")
    out.append(f"question_bank={banks} questions={questions}")
    out.append(f"papers={len(papers)} " + " | ".join(f"{row[0]}:{row[2]}:{row[3]}" for row in papers))
    out.append(f"homework submitted/graded={homework_submitted} doing={homework_doing} not_started={homework_not_started}")
    out.append(f"knowledge_docs={docs} chunks={chunks} searchable={searchable}")
    out.append(f"activity_days={activity_days} last7={last7} last30={last30} older90={old}")
    out.append(f"bot_config={bot[0] if bot else None}")
    out.append(f"xp={xp_rows[:3]} ...")
    assert teacher == 1, "教师数不是 1"
    assert klass == 1, "demo 班级不存在"
    assert students == 10, "学生数不是 10"
    assert banks >= 1 and questions >= 20, "题库/题目不足"
    assert len(papers) == 2 and {row[2] for row in papers} == {"homework", "practice"}, "两试卷不完整"
    assert homework_submitted == 4 and homework_doing == 2 and homework_not_started == 4, "作业分布不是 4/2/4"
    assert docs >= 2 and chunks >= 4 and searchable > 0, "知识文档/切片不可检索"
    assert activity_days > 0 and last7 > 0 and last30 > 0 and old > 0, "活动覆盖不足"
    assert bot and bot[0][0] == 1 and bot[0][7] == 1, "bot_config 未启用"
    assert bot[0][10] is None and bot[0][11] is None, "群/教师 openid 必须留空"
    assert bot[0][12] == "never", "last_check_status 必须 never"
    assert bot[0][13] == "env", "app_id 必须为 env 占位"
    assert all(row[1] == 400 and row[2] == 3 and row[3] == 400 for row in xp_rows), "XP 与每日经验不一致"
    out.append("RESULT: PASS")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sqlite", type=Path)
    group.add_argument("--database-url")
    args = parser.parse_args()
    close = None
    try:
        if args.sqlite:
            dialect, execute, close = _sqlite_executor(args.sqlite)
        else:
            dialect, execute, close = _url_executor(args.database_url)
        for line in run(dialect, execute, close):
            print(line)
        return 0
    except AssertionError as exc:
        print(f"RESULT: FAIL {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"RESULT: ERROR {type(exc).__name__}: {exc}")
        return 1
    finally:
        if close:
            close()


if __name__ == "__main__":
    sys.exit(main())
