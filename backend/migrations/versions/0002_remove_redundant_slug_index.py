"""Remove the redundant non-unique problem slug index."""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_remove_redundant_slug_index"
down_revision: str | Sequence[str] | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_problems_slug", table_name="problems")


def downgrade() -> None:
    op.create_index("ix_problems_slug", "problems", ["slug"], unique=False)
