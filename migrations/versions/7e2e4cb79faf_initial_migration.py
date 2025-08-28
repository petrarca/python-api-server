"""Initial migration

Revision ID: 7e2e4cb79faf
Revises:
Create Date: 2025-03-10 14:25:00.000000
"""

import contextlib
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7e2e4cb79faf"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Constants for frequently used values
UUID_GEN = "uuid_generate_v4()"
TIMESTAMP_NOW = "now()"


def upgrade() -> None:
    """Create the initial database schema following the sequence in schema.sql."""
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create patients table first
    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(), server_default=sa.text(UUID_GEN), nullable=False),
        sa.Column("patient_id", sa.String(50), nullable=False, unique=True),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(10), nullable=True),
        sa.Column("blood_type", sa.String(10), nullable=True),
        sa.Column("height", sa.String(20), nullable=True),
        sa.Column("weight", sa.String(20), nullable=True),
        sa.Column("primary_physician", sa.String(100), nullable=True),
        sa.Column("insurance_provider", sa.String(100), nullable=True),
        sa.Column("insurance_number", sa.String(50), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("conditions", postgresql.ARRAY(sa.String()), server_default=sa.text("ARRAY[]::character varying[]"), nullable=False),
        sa.Column("allergies", postgresql.ARRAY(sa.String()), server_default=sa.text("ARRAY[]::character varying[]"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text(TIMESTAMP_NOW), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text(TIMESTAMP_NOW), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create addresses table with reference to patients
    op.create_table(
        "addresses",
        sa.Column("id", postgresql.UUID(), server_default=sa.text(UUID_GEN), nullable=False),
        sa.Column("patient_id", postgresql.UUID(), nullable=False),
        sa.Column("address_type", sa.String(20), nullable=False),
        sa.Column("address_line", sa.Text(), nullable=False),
        sa.Column("street", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("zip_code", sa.String(20), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text(TIMESTAMP_NOW), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text(TIMESTAMP_NOW), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add primary_address column to patients with reference to addresses
    with op.batch_alter_table("patients", schema=None) as batch_op:
        batch_op.add_column(sa.Column("primary_address", postgresql.UUID(), nullable=True))
        batch_op.create_foreign_key("patients_primary_address_fkey", "addresses", ["primary_address"], ["id"], ondelete="SET NULL")

    # Create indexes
    op.create_index("idx_patients_patient_id", "patients", ["patient_id"], unique=False)
    op.create_index("idx_patients_allergies", "patients", ["allergies"], postgresql_using="gin")
    op.create_index("idx_addresses_patient_id", "addresses", ["patient_id"], unique=False)

    # Create updated_at triggers
    op.execute("""
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    """)

    op.execute("""
    CREATE TRIGGER update_patients_updated_at
        BEFORE UPDATE ON patients
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
    CREATE TRIGGER update_addresses_updated_at
        BEFORE UPDATE ON addresses
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # Create health check function
    op.execute("""
    CREATE OR REPLACE FUNCTION health_check()
    RETURNS boolean AS $$
    BEGIN
      -- Simple health check that verifies database connection
      -- and basic functionality
      RETURN TRUE;
    END;
    $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    """Drop all tables in the correct order to handle foreign key constraints."""
    # Drop tables in reverse order to handle foreign key constraints

    # Remove primary_address from patients before dropping addresses
    with op.batch_alter_table("patients", schema=None) as batch_op:
        with contextlib.suppress(sa.exc.OperationalError):
            batch_op.drop_constraint("patients_primary_address_fkey", type_="foreignkey")
        batch_op.drop_column("primary_address")

    op.drop_table("addresses")
    op.drop_table("patients")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS health_check()")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
