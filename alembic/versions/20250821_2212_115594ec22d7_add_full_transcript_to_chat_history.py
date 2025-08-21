"""add_full_transcript_to_chat_history

Revision ID: 115594ec22d7
Revises: d3e2a4d24c6d
Create Date: 2025-08-21 22:12:46.817417

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "115594ec22d7"
down_revision = "d3e2a4d24c6d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add full_transcript column to chat_history table
    op.add_column(
        "chat_history",
        sa.Column("full_transcript", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    # Remove full_transcript column from chat_history table
    op.drop_column("chat_history", "full_transcript")
