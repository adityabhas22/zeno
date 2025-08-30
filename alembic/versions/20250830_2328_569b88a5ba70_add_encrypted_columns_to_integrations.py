"""add_encrypted_columns_to_integrations

Revision ID: 569b88a5ba70
Revises: 115594ec22d7
Create Date: 2025-08-30 23:28:41.188521

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "569b88a5ba70"
down_revision = "115594ec22d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add encrypted columns to integrations table for secure storage
    op.add_column("integrations", sa.Column("encrypted_auth_tokens", sa.Text(), nullable=True))
    op.add_column("integrations", sa.Column("encrypted_config_data", sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove encrypted columns from integrations table
    op.drop_column("integrations", "encrypted_config_data")
    op.drop_column("integrations", "encrypted_auth_tokens")
