"""Player opponent analysis agent table

Revision ID: player_opponent_analysis_v1
Revises: agent_analytics_v1
Create Date: 2026-07-27

"""
from alembic import op
import sqlalchemy as sa


revision = "player_opponent_analysis_v1"
down_revision = "agent_analytics_v1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "player_opponent_analysis",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=10), nullable=False),
        sa.Column("opponent_team_id", sa.Integer(), nullable=False),
        sa.Column("opponent_team_abbr", sa.String(length=8), nullable=True),
        sa.Column("game_date", sa.Date(), nullable=True),
        sa.Column("is_home_game", sa.Boolean(), nullable=True),
        sa.Column("h2h_avg_pts", sa.Float(), nullable=True),
        sa.Column("h2h_avg_reb", sa.Float(), nullable=True),
        sa.Column("h2h_avg_ast", sa.Float(), nullable=True),
        sa.Column("h2h_games_played", sa.Integer(), nullable=True),
        sa.Column("def_rank_pts", sa.Integer(), nullable=True),
        sa.Column("def_rank_reb", sa.Integer(), nullable=True),
        sa.Column("def_rank_ast", sa.Integer(), nullable=True),
        sa.Column("def_rank_3pm", sa.Integer(), nullable=True),
        sa.Column("off_rank_pts", sa.Integer(), nullable=True),
        sa.Column("off_rank_reb", sa.Integer(), nullable=True),
        sa.Column("off_rank_ast", sa.Integer(), nullable=True),
        sa.Column("off_rank_3pm", sa.Integer(), nullable=True),
        sa.Column("position", sa.String(length=8), nullable=True),
        sa.Column("pos_def_rank_pts", sa.Integer(), nullable=True),
        sa.Column("pos_def_rank_reb", sa.Integer(), nullable=True),
        sa.Column("pos_def_rank_ast", sa.Integer(), nullable=True),
        sa.Column("pos_def_rank_3pm", sa.Integer(), nullable=True),
        sa.Column("matchup_adv_pts", sa.Float(), nullable=True),
        sa.Column("matchup_adv_reb", sa.Float(), nullable=True),
        sa.Column("matchup_adv_ast", sa.Float(), nullable=True),
        sa.Column("matchup_adv_3pm", sa.Float(), nullable=True),
        sa.Column("opponent_win_rate", sa.Float(), nullable=True),
        sa.Column("opponent_conference_rank", sa.Integer(), nullable=True),
        sa.Column("team_win_rate", sa.Float(), nullable=True),
        sa.Column("team_conference_rank", sa.Integer(), nullable=True),
        sa.Column("team_recent_form", sa.Float(), nullable=True),
        sa.Column("rest_days", sa.Integer(), nullable=True),
        sa.Column("is_injured", sa.Boolean(), nullable=True),
        sa.Column("injury_status", sa.String(length=32), nullable=True),
        sa.Column("injury_description", sa.Text(), nullable=True),
        sa.Column("formula_version", sa.String(length=32), nullable=False),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "player_id",
            "opponent_team_id",
            "season",
            name="uq_player_opponent_analysis",
        ),
    )
    op.create_index(
        "idx_poa_player_season", "player_opponent_analysis", ["player_id", "season"]
    )
    op.create_index("idx_poa_game_date", "player_opponent_analysis", ["game_date"])
    op.create_index(
        "ix_player_opponent_analysis_player_id",
        "player_opponent_analysis",
        ["player_id"],
    )
    op.create_index(
        "ix_player_opponent_analysis_season",
        "player_opponent_analysis",
        ["season"],
    )
    op.create_index(
        "ix_player_opponent_analysis_opponent_team_id",
        "player_opponent_analysis",
        ["opponent_team_id"],
    )


def downgrade():
    op.drop_index(
        "ix_player_opponent_analysis_opponent_team_id",
        table_name="player_opponent_analysis",
    )
    op.drop_index(
        "ix_player_opponent_analysis_season", table_name="player_opponent_analysis"
    )
    op.drop_index(
        "ix_player_opponent_analysis_player_id", table_name="player_opponent_analysis"
    )
    op.drop_index("idx_poa_game_date", table_name="player_opponent_analysis")
    op.drop_index("idx_poa_player_season", table_name="player_opponent_analysis")
    op.drop_table("player_opponent_analysis")
