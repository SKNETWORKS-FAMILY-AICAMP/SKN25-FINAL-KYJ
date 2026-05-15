"""create normalized profile storage

Revision ID: 20260513_0001
Revises:
Create Date: 2026-05-13
"""

from __future__ import annotations

from alembic import op

revision = "20260513_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    _create_document_profiles()
    _create_outbox_events()


def downgrade() -> None:
    for table_name in (
        "outbox_events",
        "document_profiles",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")


def _create_document_profiles() -> None:
    op.execute(
        """
        CREATE TABLE document_profiles (
            document_id text PRIMARY KEY CHECK (length(btrim(document_id)) > 0),
            tenant text NOT NULL CHECK (length(btrim(tenant)) > 0),
            document_type text NOT NULL CHECK (length(btrim(document_type)) > 0),
            source_version text NOT NULL CHECK (length(btrim(source_version)) > 0),
            profile_version text NOT NULL CHECK (length(btrim(profile_version)) > 0),
            profile_schema_version text NOT NULL DEFAULT '1' CHECK (
                length(btrim(profile_schema_version)) > 0
            ),
            title text NOT NULL CHECK (length(btrim(title)) > 0),
            summary text NOT NULL CHECK (length(btrim(summary)) > 0),
            concepts_json jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (
                jsonb_typeof(concepts_json) = 'array'
            ),
            profile_confidence double precision CHECK (
                profile_confidence IS NULL
                OR (profile_confidence >= 0.0 AND profile_confidence <= 1.0)
            ),
            model text NOT NULL DEFAULT '',
            prompt_version text NOT NULL DEFAULT '',
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
                jsonb_typeof(metadata) = 'object'
            ),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )


def _create_outbox_events() -> None:
    op.execute(
        """
        CREATE TABLE outbox_events (
            id uuid PRIMARY KEY,
            sequence bigint GENERATED ALWAYS AS IDENTITY UNIQUE NOT NULL,
            aggregate_type text NOT NULL CHECK (
                aggregate_type IN ('DOCUMENT', 'FOLDER')
            ),
            aggregate_id text NOT NULL CHECK (length(btrim(aggregate_id)) > 0),
            event_key text NOT NULL CHECK (
                event_key = aggregate_type || ':' || aggregate_id
            ),
            event_type text NOT NULL CHECK (
                event_type IN (
                    'DOCUMENT_INDEXED',
                    'DOCUMENT_DELETED',
                    'FOLDER_INDEXED',
                    'FOLDER_DELETED'
                )
            ),
            event_schema_version text NOT NULL DEFAULT '1' CHECK (
                length(btrim(event_schema_version)) > 0
            ),
            payload jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
                jsonb_typeof(payload) = 'object'
            ),
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX outbox_events_aggregate_sequence_idx
        ON outbox_events (aggregate_type, aggregate_id, sequence DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX outbox_events_key_sequence_idx
        ON outbox_events (event_key, sequence DESC)
        """
    )
