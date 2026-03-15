"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────
    op.create_table("users",
        sa.Column("id",                   UUID,          primary_key=True),
        sa.Column("username",             sa.String(80), nullable=False, unique=True),
        sa.Column("email",                sa.String(255),nullable=False, unique=True),
        sa.Column("hashed_password",      sa.String(255),nullable=False),
        sa.Column("role",                 sa.String(30), nullable=False, default="observer"),
        sa.Column("point_balance",        sa.Integer,    nullable=False, default=0),
        sa.Column("is_active",            sa.Boolean,    default=True),
        sa.Column("person_graph_path",    sa.String(512),nullable=True),
        sa.Column("person_graph_public",  sa.Boolean,    default=False),
        sa.Column("created_at",           sa.DateTime,   server_default=sa.func.now()),
        sa.Column("updated_at",           sa.DateTime,   nullable=True),
    )
    op.create_index("ix_users_username", "users", ["username"])

    # ── projects ───────────────────────────────────────────────────────────
    op.create_table("projects",
        sa.Column("id",           UUID,           primary_key=True),
        sa.Column("slug",         sa.String(120), nullable=False, unique=True),
        sa.Column("title",        sa.String(255), nullable=False),
        sa.Column("description",  sa.Text,        nullable=True),
        sa.Column("project_type", sa.String(30),  nullable=False, default="mixed"),
        sa.Column("source_url",   sa.String(512), nullable=True),
        sa.Column("is_public",    sa.Boolean,     default=True),
        sa.Column("owner_id",     UUID,           sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at",   sa.DateTime,    server_default=sa.func.now()),
    )
    op.create_index("ix_projects_slug", "projects", ["slug"])

    # ── project_versions ───────────────────────────────────────────────────
    op.create_table("project_versions",
        sa.Column("id",                     UUID,           primary_key=True),
        sa.Column("project_id",             UUID,           sa.ForeignKey("projects.id"),nullable=False),
        sa.Column("version_number",         sa.Integer,     nullable=False, default=1),
        sa.Column("crawl_timestamp",        sa.DateTime,    nullable=False),
        sa.Column("source_commit",          sa.String(64),  nullable=True),
        sa.Column("source_snapshot",        sa.String(512), nullable=True),
        sa.Column("graph_path",             sa.String(512), nullable=True),
        sa.Column("projections_dir",        sa.String(512), nullable=True),
        sa.Column("wiki_dir",               sa.String(512), nullable=True),
        sa.Column("scripts_dir",            sa.String(512), nullable=True),
        sa.Column("corpus_stats",           JSONB,          nullable=True),
        sa.Column("extraction_prompt_hash", sa.String(64),  nullable=True),
        sa.Column("model_name",             sa.String(64),  nullable=True),
        sa.Column("model_version",          sa.String(64),  nullable=True),
        sa.Column("is_active",              sa.Boolean,     default=True),
        sa.Column("created_at",             sa.DateTime,    server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "version_number", name="uq_project_version"),
    )
    op.create_index("ix_project_versions_project_id", "project_versions", ["project_id"])

    # ── tasks ──────────────────────────────────────────────────────────────
    op.create_table("tasks",
        sa.Column("id",                  sa.String(128), primary_key=True),
        sa.Column("project_version_id",  UUID,           sa.ForeignKey("project_versions.id"),nullable=False),
        sa.Column("projection_type",     sa.String(60),  nullable=False),
        sa.Column("label",               sa.String(255), nullable=False),
        sa.Column("difficulty",          sa.String(20),  nullable=False, default="standard"),
        sa.Column("output_format",       sa.String(30),  nullable=False, default="video"),
        sa.Column("duration_estimate_s", sa.Integer,     nullable=True),
        sa.Column("assembly_weight",     sa.Float,       nullable=False, default=1.0),
        sa.Column("script_path",         sa.String(512), nullable=True),
        sa.Column("bundle_path",         sa.String(512), nullable=True),
        sa.Column("graph_nodes",         JSONB,          nullable=True),
        sa.Column("style_hint",          sa.Text,        nullable=True),
        sa.Column("output_spec",         JSONB,          nullable=True),
        sa.Column("status",              sa.String(20),  nullable=False, default="open"),
        sa.Column("submission_count",    sa.Integer,     nullable=False, default=0),
        sa.Column("accepted_count",      sa.Integer,     nullable=False, default=0),
        sa.Column("base_value",          sa.Integer,     nullable=False, default=100),
        sa.Column("scarcity",            sa.Float,       nullable=False, default=1.0),
        sa.Column("current_bounty",      sa.Float,       nullable=False, default=100.0),
        sa.Column("created_at",          sa.DateTime,    server_default=sa.func.now()),
        sa.Column("updated_at",          sa.DateTime,    nullable=True),
    )
    op.create_index("ix_tasks_project_version_id", "tasks", ["project_version_id"])
    op.create_index("ix_tasks_status",             "tasks", ["status"])

    # ── task_dependencies ──────────────────────────────────────────────────
    op.create_table("task_dependencies",
        sa.Column("id",           UUID,           primary_key=True),
        sa.Column("from_task_id", sa.String(128), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("to_task_id",   sa.String(128), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("via",          sa.String(128), nullable=True),
        sa.UniqueConstraint("from_task_id", "to_task_id", name="uq_task_dep"),
    )

    # ── claims ─────────────────────────────────────────────────────────────
    op.create_table("claims",
        sa.Column("id",           UUID,           primary_key=True),
        sa.Column("user_id",      UUID,           sa.ForeignKey("users.id"),  nullable=False),
        sa.Column("task_id",      sa.String(128), sa.ForeignKey("tasks.id"),  nullable=False),
        sa.Column("status",       sa.String(20),  nullable=False, default="active"),
        sa.Column("claimed_at",   sa.DateTime,    server_default=sa.func.now()),
        sa.Column("expires_at",   sa.DateTime,    nullable=False),
        sa.Column("withdrawn_at", sa.DateTime,    nullable=True),
    )
    op.create_index("ix_claims_user_id", "claims", ["user_id"])
    op.create_index("ix_claims_task_id", "claims", ["task_id"])

    # ── submissions ────────────────────────────────────────────────────────
    op.create_table("submissions",
        sa.Column("id",             UUID,           primary_key=True),
        sa.Column("claim_id",       UUID,           sa.ForeignKey("claims.id"),  nullable=False),
        sa.Column("task_id",        sa.String(128), sa.ForeignKey("tasks.id"),   nullable=False),
        sa.Column("user_id",        UUID,           sa.ForeignKey("users.id"),   nullable=False),
        sa.Column("status",         sa.String(20),  nullable=False, default="pending"),
        sa.Column("branch_label",   sa.String(120), nullable=True),
        sa.Column("original_path",  sa.String(512), nullable=True),
        sa.Column("preview_path",   sa.String(512), nullable=True),
        sa.Column("thumbnail_path", sa.String(512), nullable=True),
        sa.Column("media_metadata", JSONB,          nullable=True),
        sa.Column("file_hash",      sa.String(64),  nullable=True),
        sa.Column("notes",          sa.Text,        nullable=True),
        sa.Column("submitted_at",   sa.DateTime,    server_default=sa.func.now()),
        sa.Column("reviewed_at",    sa.DateTime,    nullable=True),
    )
    op.create_index("ix_submissions_task_id", "submissions", ["task_id"])
    op.create_index("ix_submissions_user_id", "submissions", ["user_id"])

    # ── submission_reviews ─────────────────────────────────────────────────
    op.create_table("submission_reviews",
        sa.Column("id",            UUID, primary_key=True),
        sa.Column("submission_id", UUID, sa.ForeignKey("submissions.id"), nullable=False),
        sa.Column("reviewer_id",   UUID, sa.ForeignKey("users.id"),       nullable=False),
        sa.Column("verdict",       sa.String(30), nullable=False),
        sa.Column("notes",         sa.Text,       nullable=True),
        sa.Column("reviewed_at",   sa.DateTime,   server_default=sa.func.now()),
    )
    op.create_index("ix_reviews_submission_id", "submission_reviews", ["submission_id"])

    # ── assemblies ─────────────────────────────────────────────────────────
    op.create_table("assemblies",
        sa.Column("id",                 UUID,          primary_key=True),
        sa.Column("project_version_id", UUID,          sa.ForeignKey("project_versions.id"), nullable=False),
        sa.Column("assembler_id",       UUID,          sa.ForeignKey("users.id"), nullable=True),
        sa.Column("title",              sa.String(255),nullable=True),
        sa.Column("description",        sa.Text,       nullable=True),
        sa.Column("spec_path",          sa.String(512),nullable=True),
        sa.Column("output_path",        sa.String(512),nullable=True),
        sa.Column("status",             sa.String(40), nullable=False, default="draft"),
        sa.Column("created_at",         sa.DateTime,   server_default=sa.func.now()),
        sa.Column("updated_at",         sa.DateTime,   nullable=True),
    )
    op.create_index("ix_assemblies_project_version_id", "assemblies", ["project_version_id"])

    # ── assembly_segments ──────────────────────────────────────────────────
    op.create_table("assembly_segments",
        sa.Column("id",            UUID,           primary_key=True),
        sa.Column("assembly_id",   UUID,           sa.ForeignKey("assemblies.id"),  nullable=False),
        sa.Column("task_id",       sa.String(128), sa.ForeignKey("tasks.id"),       nullable=False),
        sa.Column("submission_id", UUID,           sa.ForeignKey("submissions.id"), nullable=True),
        sa.Column("position",      sa.Integer,     nullable=False),
        sa.Column("is_canonical",  sa.Boolean,     default=True),
        sa.Column("branch_label",  sa.String(120), nullable=True),
        sa.Column("notes",         sa.Text,        nullable=True),
    )
    op.create_index("ix_segments_assembly_id", "assembly_segments", ["assembly_id"])

    # ── point_ledger ───────────────────────────────────────────────────────
    op.create_table("point_ledger",
        sa.Column("id",            UUID,           primary_key=True),
        sa.Column("user_id",       UUID,           sa.ForeignKey("users.id"),       nullable=False),
        sa.Column("event_type",    sa.String(40),  nullable=False),
        sa.Column("delta",         sa.Integer,     nullable=False),
        sa.Column("balance_after", sa.Integer,     nullable=False),
        sa.Column("task_id",       sa.String(128), sa.ForeignKey("tasks.id"),       nullable=True),
        sa.Column("submission_id", UUID,           sa.ForeignKey("submissions.id"), nullable=True),
        sa.Column("assembly_id",   UUID,           sa.ForeignKey("assemblies.id"),  nullable=True),
        sa.Column("description",   sa.Text,        nullable=True),
        sa.Column("created_at",    sa.DateTime,    server_default=sa.func.now()),
    )
    op.create_index("ix_ledger_user_id", "point_ledger", ["user_id"])


def downgrade() -> None:
    for table in [
        "point_ledger", "assembly_segments", "assemblies",
        "submission_reviews", "submissions", "claims",
        "task_dependencies", "tasks", "project_versions",
        "projects", "users",
    ]:
        op.drop_table(table)
