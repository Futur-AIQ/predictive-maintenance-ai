"""Initial migration - all tables

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "engineer", name="userrole"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "work_orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("work_order_id", sa.String(length=36), nullable=False),
        sa.Column("equipment_id", sa.String(length=100), nullable=False),
        sa.Column("fault_code", sa.String(length=50), nullable=True),
        sa.Column("fault_description", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="severity"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED", name="workorderstatus"),
            nullable=True,
        ),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("priority_score", sa.Float(), nullable=True),
        sa.Column("estimated_completion_hours", sa.Float(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_order_id"),
    )
    op.create_index(op.f("ix_work_orders_equipment_id"), "work_orders", ["equipment_id"])

    op.create_table(
        "diagnostic_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.String(length=100), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("work_order_id", sa.String(length=36), nullable=True),
        sa.Column("sources_used", sa.JSON(), nullable=True),
        sa.Column("agent_steps", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )


def downgrade() -> None:
    op.drop_table("diagnostic_sessions")
    op.drop_index(op.f("ix_work_orders_equipment_id"), table_name="work_orders")
    op.drop_table("work_orders")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
