-- This file is executed by its Alembic revision. Keep statements in dependency order.

-- document_index_records
CREATE TABLE document_index_records (
    document_id text PRIMARY KEY
        REFERENCES document_sources (document_id)
        ON DELETE CASCADE,
    index_input_digest text NOT NULL CHECK (
        length(btrim(index_input_digest)) > 0
    ),
    signal_generation_version text NOT NULL DEFAULT '1' CHECK (
        length(btrim(signal_generation_version)) > 0
    ),
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
    tenant_id text NOT NULL,
    document_id text NOT NULL,
    index_input_digest text NOT NULL CHECK (
        length(btrim(index_input_digest)) > 0
    ),
    chunk_index integer NOT NULL CHECK (chunk_index >= 0),
    search_text text NOT NULL CHECK (length(btrim(search_text)) > 0),
    source_start_offset integer NOT NULL CHECK (source_start_offset >= 0),
    source_end_offset integer NOT NULL CHECK (
        source_end_offset >= source_start_offset
    ),
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('simple', search_text)
    ) STORED,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, document_id, chunk_index),
    FOREIGN KEY (tenant_id, document_id)
        REFERENCES document_sources (tenant_id, document_id)
        ON DELETE CASCADE
);

-- document_signals
CREATE TABLE document_signals (
    signal_id text PRIMARY KEY CHECK (length(btrim(signal_id)) > 0),
    document_id text NOT NULL
        REFERENCES document_sources (document_id)
        ON DELETE CASCADE,
    index_input_digest text NOT NULL CHECK (
        length(btrim(index_input_digest)) > 0
    ),
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
    generation_model text CHECK (
        generation_model IS NULL OR length(btrim(generation_model)) > 0
    ),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (document_id, signal_type, signal_key)
);
