"""Add journy_stage, preferences, health_score to customer

Revision ID: 096a868b6929
Revises: 1e332cfb54f1
Create Date: 2026-04-26 09:29:00.897085

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '096a868b6929'
down_revision: Union[str, Sequence[str], None] = '1e332cfb54f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    journey_stage_enum = sa.Enum('prospect', 'onboarding', 'active', 'at_risk', 'champion', name='journeystage')
    journey_stage_enum.create(op.get_bind())
    op.add_column('customers', sa.Column('journey_stage', journey_stage_enum, nullable=False, server_default='prospect'))
    op.add_column('customers', sa.Column('preferences', sa.JSON(), nullable=True))
    op.add_column('customers', sa.Column('health_score', sa.Float(), nullable=False, server_default='0.0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('customers', 'health_score')
    op.drop_column('customers', 'preferences')
    op.drop_column('customers', 'journey_stage')
    sa.Enum(name='journeystage').drop(op.get_bind())
