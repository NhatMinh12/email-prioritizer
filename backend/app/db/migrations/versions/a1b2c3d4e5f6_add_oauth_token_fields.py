"""add_oauth_token_fields

Revision ID: a1b2c3d4e5f6
Revises: 5ae8fdd96302
Create Date: 2026-03-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "5ae8fdd96302"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("oauth_access_token", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("oauth_refresh_token", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column("oauth_token_expiry", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "oauth_token_expiry")
    op.drop_column("users", "oauth_refresh_token")
    op.drop_column("users", "oauth_access_token")
