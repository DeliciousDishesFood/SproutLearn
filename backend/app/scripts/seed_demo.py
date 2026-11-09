"""演示数据说明：M1 不内置初始化功能，请使用独立 seed_data.sql。

执行顺序（在数据库容器内或本机 mysql 客户端）：
1. 先执行 deploy/db/schema.sql（或 alembic upgrade head）
2. 再执行文档仓库 docs/demo/seed_data.sql
路径：E:\\ai-dev-projects\\智能助学平台\\docs\\demo\\seed_data.sql
"""

from __future__ import annotations

SEED_SQL_PATH = r"E:\ai-dev-projects\智能助学平台\docs\demo\seed_data.sql"


def main() -> None:
    print("M1 不在应用内初始化演示数据。")
    print(f"请先建表，再手动执行：{SEED_SQL_PATH}")


if __name__ == "__main__":
    main()
