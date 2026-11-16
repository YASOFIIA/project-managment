# Migration: add user email
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Add email column with unique index to users table
def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email", sa.String(length=255), server_default="", nullable=False),
    )
    op.execute("UPDATE users SET email = login || '@localhost' WHERE email = ''")
    op.create_index(
        op.f("ix_users_email"),
        "users",
        ["email"],
        unique=True,
    )
    op.alter_column("users", "email", server_default=None)


# Remove email column and index from users table
def downgrade() -> None:
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_column("users", "email")
