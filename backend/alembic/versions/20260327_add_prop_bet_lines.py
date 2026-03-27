"""Add prop_bet_lines for The Odds API synced lines

Revision ID: prop_bet_lines_v1
Revises: prop_pred_records
Create Date: 2026-03-27

"""
from alembic import op
import sqlalchemy as sa


revision = 'prop_bet_lines_v1'
down_revision = 'prop_pred_records'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'prop_bet_lines',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=True),
        sa.Column('game_date', sa.Date(), nullable=True),
        sa.Column('prop_type', sa.String(length=32), nullable=True),
        sa.Column('line_value', sa.Float(), nullable=True),
        sa.Column('over_odds', sa.Float(), nullable=True),
        sa.Column('under_odds', sa.Float(), nullable=True),
        sa.Column('source', sa.String(length=64), nullable=True),
        sa.Column('nba_event_id', sa.String(length=64), nullable=True),
        sa.Column('commence_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], name='fk_prop_bet_lines_player'),
    )
    op.create_index('idx_prop_bet_lines_player_date', 'prop_bet_lines', ['player_id', 'game_date'])
    op.create_index('idx_prop_bet_lines_game_prop', 'prop_bet_lines', ['game_date', 'prop_type'])
    op.create_index('idx_prop_bet_lines_event', 'prop_bet_lines', ['nba_event_id'])


def downgrade():
    op.drop_index('idx_prop_bet_lines_event', table_name='prop_bet_lines')
    op.drop_index('idx_prop_bet_lines_game_prop', table_name='prop_bet_lines')
    op.drop_index('idx_prop_bet_lines_player_date', table_name='prop_bet_lines')
    op.drop_table('prop_bet_lines')
