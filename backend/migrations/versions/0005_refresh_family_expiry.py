"""Track an absolute expiry for each refresh-token family."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_refresh_family_expiry"
down_revision: str | Sequence[str] | None = "0004_authentication"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "refresh_sessions",
        sa.Column("family_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE refresh_sessions SET family_expires_at = expires_at")
    op.alter_column("refresh_sessions", "family_expires_at", nullable=False)


def downgrade() -> None:
    op.drop_column("refresh_sessions", "family_expires_at")
