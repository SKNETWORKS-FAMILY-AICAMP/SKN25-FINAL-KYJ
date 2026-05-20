-- This file is executed by its Alembic revision. Keep statements in dependency order.

-- document_index_records
CREATE TABLE document_index_records (
    document_id text PRIMARY KEY
        REFERENCES document_sources (document_id)
        ON DELETE CASCADE,
    signal_set_version text NOT NULL DEFAULT '1' CHECK (
        length(btrim(signal_set_version)) > 0
    ),
    model text NOT NULL DEFAULT '',
    deleted_at timestamptz,
    purge_after timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (
        purge_after IS NULL
        OR (
            deleted_at IS NOT NULL
            AND purge_after >= deleted_at
        )
    )
);

-- document_chunks
CREATE TABLE document_chunks (
    chunk_id uuid PRIMARY KEY,
    document_id text NOT NULL
        REFERENCES document_sources (document_id)
        ON DELETE CASCADE,
    chunk_index integer NOT NULL CHECK (chunk_index >= 0),
    text_digest text NOT NULL CHECK (length(btrim(text_digest)) > 0),
    start_offset integer NOT NULL CHECK (start_offset >= 0),
    end_offset integer NOT NULL CHECK (end_offset >= start_offset),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (document_id, chunk_index)
);

-- document_signals
CREATE TABLE document_signals (
    signal_id text PRIMARY KEY CHECK (length(btrim(signal_id)) > 0),
    document_id text NOT NULL
        REFERENCES document_sources (document_id)
        ON DELETE CASCADE,
    signal_type text NOT NULL CHECK (
        signal_type IN (
            'summary',
            'concept',
            'entity',
            'issue',
            'commitment',
            'claim'
        )
    ),
    signal_key text NOT NULL CHECK (length(btrim(signal_key)) > 0),
    text text NOT NULL CHECK (length(btrim(text)) > 0),
    attributes_json jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
        jsonb_typeof(attributes_json) = 'object'
    ),
    evidence_json jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (
        jsonb_typeof(evidence_json) = 'array'
    ),
    confidence double precision CHECK (
        confidence IS NULL OR confidence BETWEEN 0.0 AND 1.0
    ),
    extractor_name text NOT NULL CHECK (length(btrim(extractor_name)) > 0),
    extractor_version text NOT NULL CHECK (
        length(btrim(extractor_version)) > 0
    ),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
