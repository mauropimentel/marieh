"""initial tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-14 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "instructors",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("max_students_per_slot", sa.Integer(), nullable=False),
        sa.Column("google_calendar_id", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "students",
        sa.Column("cpf", sa.String(length=20), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.PrimaryKeyConstraint("cpf"),
    )

    op.create_table(
        "class_slots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("instructor_id", sa.String(length=36), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["instructor_id"], ["instructors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "bookings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("slot_id", sa.String(length=36), nullable=False),
        sa.Column("student_cpf", sa.String(length=20), nullable=False),
        sa.Column("student_name", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=True),
        sa.Column("google_event_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["slot_id"], ["class_slots.id"]),
        sa.ForeignKeyConstraint(["student_cpf"], ["students.cpf"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bookings_external_id"), "bookings", ["external_id"], unique=False)

    op.create_table(
        "alerts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("booking_id", sa.String(length=36), nullable=True),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_index(op.f("ix_bookings_external_id"), table_name="bookings")
    op.drop_table("bookings")
    op.drop_table("class_slots")
    op.drop_table("students")
    op.drop_table("instructors")
