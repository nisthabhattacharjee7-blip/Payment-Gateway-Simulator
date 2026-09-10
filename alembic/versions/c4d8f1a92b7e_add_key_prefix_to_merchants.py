"""add key_prefix to merchants

Revision ID: c4d8f1a92b7e
Revises: 9f3c7a21ee4d
Create Date: 2026-09-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4d8f1a92b7e'
down_revision: Union[str, None] = '9f3c7a21ee4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('merchants', sa.Column('key_prefix', sa.String(), nullable=True))
    op.create_index('ix_merchants_key_prefix', 'merchants', ['key_prefix'])


def downgrade() -> None:
    op.drop_index('ix_merchants_key_prefix', table_name='merchants')
    op.drop_column('merchants', 'key_prefix')