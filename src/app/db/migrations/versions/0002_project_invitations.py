"""project_invitations

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-14 20:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: create project_invitations table."""
    op.create_table(
        "project_invitations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "used",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_project_invitations_project_id"),
        "project_invitations",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_invitations_token"),
        "project_invitations",
        ["token"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema: drop project_invitations table."""
    op.drop_index(
        op.f("ix_project_invitations_token"),
        table_name="project_invitations",
    )
    op.drop_index(
        op.f("ix_project_invitations_project_id"),
        table_name="project_invitations",
    )
    op.drop_table("project_invitations")
