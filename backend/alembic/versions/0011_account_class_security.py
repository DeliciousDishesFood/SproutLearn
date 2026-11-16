"""v1.4 迁移 0011：账号安全版本、强制改密与最小操作记录。"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0011_account_class_security"
down_revision = "0010_bot_teacher_ai"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "teacher",
        sa.Column("auth_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "teacher",
        sa.Column("must_change_password", sa.SmallInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "student",
        sa.Column("auth_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "student",
        sa.Column("must_change_password", sa.SmallInteger(), nullable=False, server_default="0"),
    )
    op.create_table(
        "account_audit_log",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer, "sqlite"),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column("actor_role", sa.String(8), nullable=False),
        sa.Column("actor_id", sa.BigInteger(), nullable=False),
        sa.Column("target_role", sa.String(8), nullable=False),
        sa.Column("target_id", sa.BigInteger(), nullable=False),
        sa.Column("class_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("result", sa.String(16), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_audit_actor", "account_audit_log", ["actor_role", "actor_id", "created_at"])
    op.create_index("idx_audit_target", "account_audit_log", ["target_role", "target_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_audit_target", table_name="account_audit_log")
    op.drop_index("idx_audit_actor", table_name="account_audit_log")
    op.drop_table("account_audit_log")
    op.drop_column("student", "must_change_password")
    op.drop_column("student", "auth_version")
    op.drop_column("teacher", "must_change_password")
    op.drop_column("teacher", "auth_version")
