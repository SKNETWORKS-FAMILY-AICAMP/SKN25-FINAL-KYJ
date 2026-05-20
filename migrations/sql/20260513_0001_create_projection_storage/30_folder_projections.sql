-- This file is executed by its Alembic revision. Keep statements in dependency order.

-- folder_index_records
CREATE TABLE folder_index_records (
    folder_id text PRIMARY KEY
        REFERENCES folder_sources (folder_id)
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

-- folder_signals
CREATE TABLE folder_signals (
    signal_id text PRIMARY KEY CHECK (length(btrim(signal_id)) > 0),
    folder_id text NOT NULL
        REFERENCES folder_sources (folder_id)
        ON DELETE CASCADE,
    signal_type text NOT NULL CHECK (
        signal_type IN (
            'summary',
            'responsibility',
            'alignment',
            'coherence',
            'outlier_document',
            'coverage_gap',
            'naming_mismatch',
            'split_suggestion',
            'merge_suggestion'
        )
    ),
    signal_key text NOT NULL CHECK (length(btrim(signal_key)) > 0),
    text text NOT NULL CHECK (length(btrim(text)) > 0),
    related_document_id text
        REFERENCES document_sources (document_id)
        ON DELETE SET NULL,
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
