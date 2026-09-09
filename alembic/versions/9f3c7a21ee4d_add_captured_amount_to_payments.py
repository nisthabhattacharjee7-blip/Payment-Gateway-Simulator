"""add captured_amount to payments
Revision ID: 9f3c7a21ee4d
Revises: 5aa16530b028
Create Date: 2026-09-08 00:00:00.000000"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '9f3c7a21ee4d'
down_revision: Union[str, None] = '5aa16530b028'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('payments', sa.Column('captured_amount', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('payments', 'captured_amount')
    