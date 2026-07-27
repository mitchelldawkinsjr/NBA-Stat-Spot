"""Agent analytics tables + validation columns on player_game_stats

Revision ID: agent_analytics_v1
Revises: pipeline_tables_v1
Create Date: 2026-07-26

"""
from alembic import op
import sqlalchemy as sa


revision = "agent_analytics_v1"
down_revision = "pipeline_tables_v1"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("player_game_stats", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("validation_status", sa.String(length=16), nullable=False, server_default="valid")
        )
        batch_op.add_column(sa.Column("validation_failures", sa.Text(), nullable=True))
        batch_op.create_index(
            "idx_pgs_season_validation",
            ["season", "validation_status"],
            unique=False,
        )

    op.create_table(
        "player_stat_windows",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=10), nullable=False),
        sa.Column("stat_type", sa.String(length=16), nullable=False),
        sa.Column("window", sa.String(length=16), nullable=False),
        sa.Column("avg", sa.Float(), nullable=True),
        sa.Column("weighted_avg", sa.Float(), nullable=True),
        sa.Column("trend", sa.String(length=16), nullable=True),
        sa.Column("trend_slope", sa.Float(), nullable=True),
        sa.Column("consistency", sa.Float(), nullable=True),
        sa.Column("heat_index", sa.Float(), nullable=True),
        sa.Column("volatility_index", sa.Float(), nullable=True),
        sa.Column("games_sample", sa.Integer(), nullable=True),
        sa.Column("formula_version", sa.String(length=32), nullable=False),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", "season", "stat_type", "window", name="uq_player_stat_windows"),
    )
    op.create_index("idx_psw_player_season", "player_stat_windows", ["player_id", "season"])

    op.create_table(
        "player_line_hit_rates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=10), nullable=False),
        sa.Column("stat_type", sa.String(length=16), nullable=False),
        sa.Column("line", sa.Float(), nullable=False),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("window", sa.String(length=16), nullable=False),
        sa.Column("hit_rate", sa.Float(), nullable=True),
        sa.Column("hits", sa.Integer(), nullable=True),
        sa.Column("total", sa.Integer(), nullable=True),
        sa.Column("formula_version", sa.String(length=32), nullable=False),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "player_id",
            "season",
            "stat_type",
            "line",
            "direction",
            "window",
            name="uq_player_line_hit_rates",
        ),
    )
    op.create_index("idx_plhr_player_season", "player_line_hit_rates", ["player_id", "season"])
    op.create_index("idx_plhr_stat_line", "player_line_hit_rates", ["stat_type", "line"])

    op.create_table(
        "player_prop_evaluations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column("season", sa.String(length=10), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("player_name", sa.String(length=128), nullable=True),
        sa.Column("stat_type", sa.String(length=16), nullable=False),
        sa.Column("display_type", sa.String(length=8), nullable=True),
        sa.Column("line", sa.Float(), nullable=False),
        sa.Column("fair_line", sa.Float(), nullable=True),
        sa.Column("market_line", sa.Float(), nullable=True),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("suggestion", sa.String(length=8), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("hit_rate", sa.Float(), nullable=True),
        sa.Column("tier", sa.String(length=16), nullable=True),
        sa.Column("is_hot", sa.Boolean(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("stats_json", sa.Text(), nullable=True),
        sa.Column("confidence_source", sa.String(length=32), nullable=True),
        sa.Column("rationale_source", sa.String(length=32), nullable=True),
        sa.Column("ml_available", sa.Boolean(), nullable=True),
        sa.Column("formula_version", sa.String(length=32), nullable=False),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "game_date",
            "player_id",
            "stat_type",
            "line",
            "direction",
            name="uq_player_prop_evaluations",
        ),
    )
    op.create_index("idx_ppe_game_date", "player_prop_evaluations", ["game_date"])
    op.create_index(
        "idx_ppe_date_confidence", "player_prop_evaluations", ["game_date", "confidence"]
    )


def downgrade():
    op.drop_index("idx_ppe_date_confidence", table_name="player_prop_evaluations")
    op.drop_index("idx_ppe_game_date", table_name="player_prop_evaluations")
    op.drop_table("player_prop_evaluations")
    op.drop_index("idx_plhr_stat_line", table_name="player_line_hit_rates")
    op.drop_index("idx_plhr_player_season", table_name="player_line_hit_rates")
    op.drop_table("player_line_hit_rates")
    op.drop_index("idx_psw_player_season", table_name="player_stat_windows")
    op.drop_table("player_stat_windows")
    with op.batch_alter_table("player_game_stats", schema=None) as batch_op:
        batch_op.drop_index("idx_pgs_season_validation")
        batch_op.drop_column("validation_failures")
        batch_op.drop_column("validation_status")
