"""Add prop_prediction_records table for self-improving pipeline

Revision ID: prop_pred_records
Revises: game_pred_insight
Create Date: 2026-03-13

"""
from alembic import op
import sqlalchemy as sa


revision = 'prop_pred_records'
down_revision = 'game_pred_insight'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'prop_prediction_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('record_date', sa.Date(), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('player_name', sa.String(128), nullable=True),
        sa.Column('stat_type', sa.String(16), nullable=False),
        sa.Column('line_value', sa.Float(), nullable=False),
        sa.Column('direction', sa.String(8), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('predicted_value', sa.Float(), nullable=True),
        sa.Column('actual_value', sa.Float(), nullable=True),
        sa.Column('error', sa.Float(), nullable=True),
        sa.Column('model_version', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('settled_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_prop_pred_date', 'prop_prediction_records', ['record_date'])
    op.create_index('idx_prop_pred_settled', 'prop_prediction_records', ['actual_value'])


def downgrade():
    op.drop_index('idx_prop_pred_settled', 'prop_prediction_records')
    op.drop_index('idx_prop_pred_date', 'prop_prediction_records')
    op.drop_table('prop_prediction_records')
