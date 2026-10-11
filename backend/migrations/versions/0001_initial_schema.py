"""Create the Phase 1 users, problems, and submissions schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=16), server_default="user", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "problems",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.String(length=16), nullable=False),
        sa.Column("time_limit_ms", sa.Integer(), server_default="1000", nullable=False),
        sa.Column("memory_limit_mb", sa.Integer(), server_default="128", nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "difficulty IN ('easy', 'medium', 'hard')", name="ck_problems_difficulty"
        ),
        sa.CheckConstraint("memory_limit_mb > 0", name="ck_problems_memory_limit_positive"),
        sa.CheckConstraint("time_limit_ms > 0", name="ck_problems_time_limit_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_problems_slug", "problems", ["slug"], unique=False)
    op.create_index(
        "ix_problems_published_title", "problems", ["is_published", "title"], unique=False
    )
    op.create_table(
        "test_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("problem_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("input_data", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=False),
        sa.Column("is_sample", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("position >= 0", name="ck_test_cases_position_nonnegative"),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("problem_id", "position", name="uq_test_cases_problem_position"),
    )
    op.create_index("ix_test_cases_problem_id", "test_cases", ["problem_id"], unique=False)
    op.create_table(
        "submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("problem_id", sa.Uuid(), nullable=False),
        sa.Column("language", sa.String(length=32), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="QUEUED", nullable=False),
        sa.Column("verdict", sa.String(length=32), server_default="NOT_EVALUATED", nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "queued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED')", name="ck_submissions_status"
        ),
        sa.CheckConstraint(
            "verdict IN ('NOT_EVALUATED', 'ACCEPTED', 'WRONG_ANSWER', 'RUNTIME_ERROR', "
            "'TIME_LIMIT_EXCEEDED', 'MEMORY_LIMIT_EXCEEDED')",
            name="ck_submissions_verdict",
        ),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_submissions_user_id", "submissions", ["user_id"], unique=False)
    op.create_index("ix_submissions_problem_id", "submissions", ["problem_id"], unique=False)
    op.create_index("ix_submissions_status", "submissions", ["status"], unique=False)
    op.create_index("ix_submissions_created_at", "submissions", ["created_at"], unique=False)
    op.create_table(
        "submission_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("test_case_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="NOT_EVALUATED", nullable=False),
        sa.Column("runtime_ms", sa.Float(), nullable=True),
        sa.Column("memory_kb", sa.Integer(), nullable=True),
        sa.Column("stdout", sa.Text(), nullable=True),
        sa.Column("stderr", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('NOT_EVALUATED', 'ACCEPTED', 'WRONG_ANSWER', 'RUNTIME_ERROR', "
            "'TIME_LIMIT_EXCEEDED', 'MEMORY_LIMIT_EXCEEDED')",
            name="ck_submission_results_status",
        ),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["test_case_id"], ["test_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_id", "test_case_id", name="uq_result_submission_test_case"),
    )
    op.create_index(
        "ix_submission_results_submission_id", "submission_results", ["submission_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_submission_results_submission_id", table_name="submission_results")
    op.drop_table("submission_results")
    op.drop_index("ix_submissions_created_at", table_name="submissions")
    op.drop_index("ix_submissions_status", table_name="submissions")
    op.drop_index("ix_submissions_problem_id", table_name="submissions")
    op.drop_index("ix_submissions_user_id", table_name="submissions")
    op.drop_table("submissions")
    op.drop_index("ix_test_cases_problem_id", table_name="test_cases")
    op.drop_table("test_cases")
    op.drop_index("ix_problems_published_title", table_name="problems")
    op.drop_index("ix_problems_slug", table_name="problems")
    op.drop_table("problems")
    op.drop_table("users")
