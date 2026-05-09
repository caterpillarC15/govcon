"""Normalized SAM dimensions + opportunity source identifiers.

Patterns aligned with govbase (agencies/subsidiaries, PSC/NAICS refs, locations,
contacts junction): dedupe + fast filters while keeping denormalized strings on
opportunities for list/API compatibility and raw_payload as audit truth.

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "psc_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("psc_code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("psc_code", name="uq_psc_codes_psc_code"),
    )
    op.create_index("ix_psc_codes_psc_code", "psc_codes", ["psc_code"], unique=False)

    op.create_table(
        "naics_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("naics_code", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("level", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("naics_code", name="uq_naics_codes_naics_code"),
    )
    op.create_index("ix_naics_codes_naics_code", "naics_codes", ["naics_code"], unique=False)

    op.create_table(
        "agencies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("agency_slug", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_agencies_code"),
    )
    op.create_index("ix_agencies_agency_slug", "agencies", ["agency_slug"], unique=False)

    op.create_table(
        "agency_subsidiaries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("parent_agency_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["parent_agency_id"], ["agencies.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "parent_agency_id", "code", name="uq_agency_subsidiaries_parent_code"
        ),
    )
    op.create_index(
        "ix_agency_subsidiaries_parent",
        "agency_subsidiaries",
        ["parent_agency_id"],
        unique=False,
    )

    op.create_table(
        "locations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("city", sa.String(length=255), nullable=True),
        sa.Column("state_code", sa.String(length=8), nullable=True),
        sa.Column("country_code", sa.String(length=8), nullable=False, server_default="US"),
        sa.Column("display_name", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_locations_state_code", "locations", ["state_code"], unique=False)

    op.create_table(
        "contacts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Extend opportunities (denorm + FKs + SAM identity) ─────────────────
    op.add_column(
        "opportunities",
        sa.Column("source_notice_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("slug", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("agency_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("agency_subsidiary_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("location_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("psc_code_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("naics_code_id", sa.Integer(), nullable=True),
    )
    op.add_column("opportunities", sa.Column("notice_type", sa.String(length=128), nullable=True))
    op.add_column("opportunities", sa.Column("posted_date", sa.Date(), nullable=True))
    op.add_column("opportunities", sa.Column("office_name", sa.String(length=512), nullable=True))
    op.add_column("opportunities", sa.Column("psc_code", sa.String(length=32), nullable=True))
    op.add_column(
        "opportunities",
        sa.Column(
            "resource_links",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "opportunities",
        sa.Column(
            "opportunity_status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
    )
    op.add_column(
        "opportunities",
        sa.Column("record_kind", sa.String(length=16), nullable=True),
    )

    op.execute(
        sa.text(
            "UPDATE opportunities SET slug = 'opp-' || REPLACE(id::text, '-', '') WHERE slug IS NULL"
        )
    )

    op.alter_column(
        "opportunities",
        "slug",
        existing_type=sa.String(length=160),
        nullable=False,
    )

    op.create_unique_constraint("uq_opportunities_slug", "opportunities", ["slug"])
    op.create_unique_constraint(
        "uq_opportunities_source_notice_id",
        "opportunities",
        ["source_notice_id"],
    )

    op.create_foreign_key(
        "fk_opportunities_agency_id_agencies",
        "opportunities",
        "agencies",
        ["agency_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_opportunities_agency_subsidiary_id",
        "opportunities",
        "agency_subsidiaries",
        ["agency_subsidiary_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_opportunities_location_id_locations",
        "opportunities",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_opportunities_psc_code_id",
        "opportunities",
        "psc_codes",
        ["psc_code_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_opportunities_naics_code_id",
        "opportunities",
        "naics_codes",
        ["naics_code_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_check_constraint(
        "ck_opportunities_opportunity_status",
        "opportunities",
        "opportunity_status IN ('open','active','closed')",
    )
    op.create_check_constraint(
        "ck_opportunities_record_kind",
        "opportunities",
        "record_kind IS NULL OR record_kind IN ('rfp','contract')",
    )

    op.create_index(
        "ix_opportunities_agency_id", "opportunities", ["agency_id"], unique=False
    )
    op.create_index(
        "ix_opportunities_posted_date", "opportunities", ["posted_date"], unique=False
    )
    op.create_index(
        "ix_opportunities_source_notice_id",
        "opportunities",
        ["source_notice_id"],
        unique=False,
    )

    op.create_table(
        "opportunity_contacts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("opportunity_id", sa.UUID(), nullable=False),
        sa.Column("contact_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=True),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"], ["contacts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "opportunity_id",
            "contact_id",
            "started_at",
            name="uq_opportunity_contacts_opp_contact_started",
        ),
    )
    op.create_index(
        "ix_opportunity_contacts_opportunity_id",
        "opportunity_contacts",
        ["opportunity_id"],
        unique=False,
    )
    op.create_index(
        "ix_opportunity_contacts_contact_id",
        "opportunity_contacts",
        ["contact_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_opportunity_contacts_contact_id", table_name="opportunity_contacts")
    op.drop_index(
        "ix_opportunity_contacts_opportunity_id", table_name="opportunity_contacts"
    )
    op.drop_table("opportunity_contacts")

    op.drop_index("ix_opportunities_source_notice_id", table_name="opportunities")
    op.drop_index("ix_opportunities_posted_date", table_name="opportunities")
    op.drop_index("ix_opportunities_agency_id", table_name="opportunities")

    op.drop_constraint("ck_opportunities_record_kind", "opportunities", type_="check")
    op.drop_constraint(
        "ck_opportunities_opportunity_status", "opportunities", type_="check"
    )

    op.drop_constraint("fk_opportunities_naics_code_id", "opportunities", type_="foreignkey")
    op.drop_constraint("fk_opportunities_psc_code_id", "opportunities", type_="foreignkey")
    op.drop_constraint(
        "fk_opportunities_location_id_locations", "opportunities", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_opportunities_agency_subsidiary_id", "opportunities", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_opportunities_agency_id_agencies", "opportunities", type_="foreignkey"
    )

    op.drop_constraint("uq_opportunities_source_notice_id", "opportunities", type_="unique")
    op.drop_constraint("uq_opportunities_slug", "opportunities", type_="unique")

    op.drop_column("opportunities", "record_kind")
    op.drop_column("opportunities", "opportunity_status")
    op.drop_column("opportunities", "resource_links")
    op.drop_column("opportunities", "psc_code")
    op.drop_column("opportunities", "office_name")
    op.drop_column("opportunities", "posted_date")
    op.drop_column("opportunities", "notice_type")
    op.drop_column("opportunities", "naics_code_id")
    op.drop_column("opportunities", "psc_code_id")
    op.drop_column("opportunities", "location_id")
    op.drop_column("opportunities", "agency_subsidiary_id")
    op.drop_column("opportunities", "agency_id")
    op.drop_column("opportunities", "slug")
    op.drop_column("opportunities", "source_notice_id")

    op.drop_table("contacts")
    op.drop_index("ix_locations_state_code", table_name="locations")
    op.drop_table("locations")
    op.drop_index("ix_agency_subsidiaries_parent", table_name="agency_subsidiaries")
    op.drop_table("agency_subsidiaries")
    op.drop_index("ix_agencies_agency_slug", table_name="agencies")
    op.drop_table("agencies")
    op.drop_index("ix_naics_codes_naics_code", table_name="naics_codes")
    op.drop_table("naics_codes")
    op.drop_index("ix_psc_codes_psc_code", table_name="psc_codes")
    op.drop_table("psc_codes")
