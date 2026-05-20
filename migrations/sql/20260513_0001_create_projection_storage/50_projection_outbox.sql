-- This file is executed by its Alembic revision. Keep statements in dependency order.

-- outbox_events
CREATE TABLE outbox_events (
    event_id uuid PRIMARY KEY,
    tenant_id text NOT NULL
        REFERENCES tenant_storage_scopes (tenant_id)
        ON DELETE CASCADE,
    event_sequence bigint GENERATED ALWAYS AS IDENTITY UNIQUE NOT NULL,
    source_kind text NOT NULL CHECK (source_kind IN ('document', 'folder')),
    source_id text NOT NULL CHECK (length(btrim(source_id)) > 0),
    partition_key text GENERATED ALWAYS AS (
        source_kind || ':' || tenant_id || ':' || source_id
    ) STORED,
    event_type text NOT NULL CHECK (
        event_type IN (
            'DOCUMENT_INDEXED',
            'DOCUMENT_DELETED',
            'DOCUMENT_FOLDER_RELATIONS_INDEXED',
            'FOLDER_INDEXED',
            'FOLDER_SIGNALS_INVALIDATED',
            'FOLDER_SIGNALS_INDEXED',
            'FOLDER_DELETED'
        )
    ),
    payload_schema_version smallint NOT NULL DEFAULT 1 CHECK (
        payload_schema_version = 1
    ),
    idempotency_key text NOT NULL CHECK (length(btrim(idempotency_key)) > 0),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
        jsonb_typeof(payload) = 'object'
    ),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, idempotency_key),
    CHECK (
        (
            source_kind = 'document'
            AND event_type IN (
                'DOCUMENT_INDEXED',
                'DOCUMENT_DELETED',
                'DOCUMENT_FOLDER_RELATIONS_INDEXED'
            )
        )
        OR (
            source_kind = 'folder'
            AND event_type IN (
                'FOLDER_INDEXED',
                'FOLDER_SIGNALS_INVALIDATED',
                'FOLDER_SIGNALS_INDEXED',
                'FOLDER_DELETED'
            )
        )
    )
);
