"""create_ai_analysis_and_medicines_tables

Revision ID: 3a7c912d8f45
Revises: e1958b089da1
Create Date: 2026-05-30 18:10:00.000000

Phase 3 — AI Analysis tables.

Creates two new tables:

  ai_analysis
  -----------
  Stores the structured result of a Gemini AI analysis for a single
  prescription.  One-to-one with ``prescriptions`` via UNIQUE constraint
  on ``prescription_id``.

  medicines
  ---------
  Stores individual medicine entries extracted by Gemini.
  One-to-many child of ``ai_analysis``.

Both tables CASCADE-delete when their parent row is removed, maintaining
full referential integrity across the chain:
    users → prescriptions → ai_analysis → medicines
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = '3a7c912d8f45'
down_revision: Union[str, None] = 'e1958b089da1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Table: ai_analysis
    # ------------------------------------------------------------------
    op.create_table(
        'ai_analysis',

        sa.Column(
            'id',
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
            comment='Surrogate primary key.',
        ),
        sa.Column(
            'prescription_id',
            sa.BigInteger(),
            nullable=False,
            comment='FK to prescriptions.id.  UNIQUE — one analysis per prescription.',
        ),
        sa.Column(
            'disease_detected',
            sa.Text(),
            nullable=True,
            comment='Disease(s) identified by Gemini from the prescription.',
        ),
        sa.Column(
            'doctor_advice',
            sa.Text(),
            nullable=True,
            comment='JSON-serialized list of doctor advice strings.',
        ),
        sa.Column(
            'lifestyle_changes',
            sa.Text(),
            nullable=True,
            comment='JSON-serialized list of lifestyle recommendation strings.',
        ),
        sa.Column(
            'raw_response',
            sa.Text().with_variant(
                sa.Text(length=4294967295),
                'mysql',
            ),
            nullable=True,
            comment='Complete raw JSON string returned by Gemini.  Never exposed to HTTP layer.',
        ),
        sa.Column(
            'analysis_status',
            sa.String(length=20),
            server_default='pending',
            nullable=False,
            comment='pending | processing | completed | failed',
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
            comment='UTC timestamp when the analysis row was first created.',
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
            comment='UTC timestamp of the last status or content update.',
        ),

        # Constraints
        sa.ForeignKeyConstraint(
            ['prescription_id'],
            ['prescriptions.id'],
            name=op.f('fk_ai_analysis_prescription_id_prescriptions'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ai_analysis')),
        sa.UniqueConstraint(
            'prescription_id',
            name='uq_ai_analysis_prescription_id',
        ),

        comment='Stores Gemini AI analysis results — one row per prescription.',
    )

    # Indexes on ai_analysis
    op.create_index(
        op.f('ix_ai_analysis_prescription_id'),
        'ai_analysis',
        ['prescription_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_ai_analysis_analysis_status'),
        'ai_analysis',
        ['analysis_status'],
        unique=False,
    )

    # ------------------------------------------------------------------
    # Table: medicines
    # ------------------------------------------------------------------
    op.create_table(
        'medicines',

        sa.Column(
            'id',
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
            comment='Surrogate primary key.',
        ),
        sa.Column(
            'analysis_id',
            sa.BigInteger(),
            nullable=False,
            comment='FK to ai_analysis.id.  Cascade-deleted when analysis is removed.',
        ),
        sa.Column(
            'medicine_name',
            sa.String(length=255),
            nullable=False,
            comment="Medicine name as extracted by Gemini, e.g. 'Metformin'.",
        ),
        sa.Column(
            'dosage',
            sa.String(length=100),
            nullable=True,
            comment="Dosage string, e.g. '500mg'.",
        ),
        sa.Column(
            'frequency',
            sa.String(length=100),
            nullable=True,
            comment="Administration frequency, e.g. '2 times daily'.",
        ),
        sa.Column(
            'duration',
            sa.String(length=100),
            nullable=True,
            comment="Course duration, e.g. '30 days'.",
        ),
        sa.Column(
            'notes',
            sa.Text(),
            nullable=True,
            comment="Extra per-medicine context returned by Gemini (e.g. 'take with food').",
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
            comment='UTC timestamp when the medicine row was created.',
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
            comment='UTC timestamp of the last update.',
        ),

        # Constraints
        sa.ForeignKeyConstraint(
            ['analysis_id'],
            ['ai_analysis.id'],
            name=op.f('fk_medicines_analysis_id_ai_analysis'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_medicines')),

        comment='Individual medicines extracted by Gemini — child of ai_analysis.',
    )

    # Index on medicines
    op.create_index(
        op.f('ix_medicines_analysis_id'),
        'medicines',
        ['analysis_id'],
        unique=False,
    )


def downgrade() -> None:
    # Drop in reverse dependency order: medicines first, then ai_analysis
    op.drop_index(op.f('ix_medicines_analysis_id'), table_name='medicines')
    op.drop_table('medicines')

    op.drop_index(op.f('ix_ai_analysis_analysis_status'), table_name='ai_analysis')
    op.drop_index(op.f('ix_ai_analysis_prescription_id'), table_name='ai_analysis')
    op.drop_table('ai_analysis')

