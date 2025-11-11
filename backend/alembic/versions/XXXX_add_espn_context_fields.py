"""Add ESPN context fields to player_contexts table

Revision ID: add_espn_context_fields
Revises: 
Create Date: 2025-01-XX

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_espn_context_fields'
down_revision = None  # Update with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    # Add ESPN identifier fields
    op.add_column('player_contexts', sa.Column('espn_team_slug', sa.String(), nullable=True))
    op.add_column('player_contexts', sa.Column('espn_player_id', sa.String(), nullable=True))
    
    # Add injury date
    op.add_column('player_contexts', sa.Column('injury_date', sa.Date(), nullable=True))
    
    # Add standings fields
    op.add_column('player_contexts', sa.Column('team_conference_rank', sa.Integer(), nullable=True))
    op.add_column('player_contexts', sa.Column('opponent_conference_rank', sa.Integer(), nullable=True))
    op.add_column('player_contexts', sa.Column('team_recent_form', sa.Float(), nullable=True))
    op.add_column('player_contexts', sa.Column('playoff_race_pressure', sa.Float(), nullable=True))
    
    # Add news/transaction fields
    op.add_column('player_contexts', sa.Column('news_sentiment', sa.Float(), nullable=True))
    op.add_column('player_contexts', sa.Column('has_recent_transaction', sa.Boolean(), nullable=True, server_default='0'))


def downgrade():
    op.drop_column('player_contexts', 'has_recent_transaction')
    op.drop_column('player_contexts', 'news_sentiment')
    op.drop_column('player_contexts', 'playoff_race_pressure')
    op.drop_column('player_contexts', 'team_recent_form')
    op.drop_column('player_contexts', 'opponent_conference_rank')
    op.drop_column('player_contexts', 'team_conference_rank')
    op.drop_column('player_contexts', 'injury_date')
    op.drop_column('player_contexts', 'espn_player_id')
    op.drop_column('player_contexts', 'espn_team_slug')

