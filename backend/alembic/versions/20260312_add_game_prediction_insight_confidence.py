"""Add insight_summary and confidence_pct to game_prediction_records

Revision ID: game_pred_insight
Revises: add_espn_context_fields
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa


revision = 'game_pred_insight'
down_revision = 'add_espn_context_fields'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'game_prediction_records',
        sa.Column('confidence_pct', sa.Float(), nullable=True),
    )
    op.add_column(
        'game_prediction_records',
        sa.Column('insight_summary', sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_column('game_prediction_records', 'insight_summary')
    op.drop_column('game_prediction_records', 'confidence_pct')
