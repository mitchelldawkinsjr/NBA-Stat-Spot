"""Pipeline tables: games, snapshots, runs, game_participants; extend player_game_stats

Revision ID: pipeline_tables_v1
Revises: prop_bet_lines_v1
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa


revision = "pipeline_tables_v1"
down_revision = "prop_bet_lines_v1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "games",
        sa.Column("game_id", sa.String(32), nullable=False),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column("season", sa.String(10), nullable=False),
        sa.Column("home_team_abbr", sa.String(8), nullable=False),
        sa.Column("away_team_abbr", sa.String(8), nullable=False),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("game_id"),
    )
    op.create_index("idx_games_date", "games", ["game_date"])
    op.create_index("idx_games_season", "games", ["season"])

    op.create_table(
        "game_participants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("game_id", sa.String(32), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", "player_id", name="uq_game_participant"),
    )
    op.create_index("idx_game_participants_game", "game_participants", ["game_id"])

    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_name", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("stats_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.String(512), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pipeline_runs_job_name", "pipeline_runs", ["job_name"])

    op.create_table(
        "ingest_watermarks",
        sa.Column("job_name", sa.String(64), nullable=False),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_game_date", sa.String(16), nullable=True),
        sa.Column("rows_written", sa.Integer(), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("job_name"),
    )

    op.create_table(
        "dashboard_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("artifact_type", sa.String(32), nullable=False),
        sa.Column("season", sa.String(10), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("built_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_snapshots_date_type", "dashboard_snapshots", ["snapshot_date", "artifact_type"])
    op.create_index(
        "idx_snapshots_published",
        "dashboard_snapshots",
        ["snapshot_date", "artifact_type", "is_published"],
    )

    with op.batch_alter_table("player_game_stats", schema=None) as batch_op:
        batch_op.add_column(sa.Column("season", sa.String(10), nullable=True))
        batch_op.add_column(sa.Column("source", sa.String(16), nullable=True))
        batch_op.add_column(sa.Column("fetched_at", sa.DateTime(), nullable=True))
        try:
            batch_op.create_unique_constraint(
                "uq_player_game_stats_player_game", ["player_id", "game_id"]
            )
        except Exception:
            pass


def downgrade():
    op.drop_table("dashboard_snapshots")
    op.drop_table("ingest_watermarks")
    op.drop_table("pipeline_runs")
    op.drop_table("game_participants")
    op.drop_table("games")
    with op.batch_alter_table("player_game_stats", schema=None) as batch_op:
        batch_op.drop_column("fetched_at")
        batch_op.drop_column("source")
        batch_op.drop_column("season")
