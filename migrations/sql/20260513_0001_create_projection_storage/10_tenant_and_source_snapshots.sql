-- This file is executed by its Alembic revision. Keep statements in dependency order.

-- tenant_storage_scopes
CREATE TABLE tenant_storage_scopes (
    tenant_id text PRIMARY KEY CHECK (length(btrim(tenant_id)) > 0),
    deleted_at timestamptz,
    purge_after timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (
        (
            deleted_at IS NULL
            AND purge_after IS NULL
        )
        OR (
            deleted_at IS NOT NULL
            AND purge_after IS NOT NULL
            AND purge_after >= deleted_at
        )
    )
);

-- document_sources
CREATE TABLE document_sources (
    document_id text PRIMARY KEY CHECK (length(btrim(document_id)) > 0),
    tenant_id text NOT NULL
        REFERENCES tenant_storage_scopes (tenant_id)
        ON DELETE CASCADE,
    document_type text CHECK (
        document_type IS NULL OR length(btrim(document_type)) > 0
    ),
    source_version text NOT NULL CHECK (length(btrim(source_version)) > 0),
    source_created_at timestamptz NOT NULL,
    source_updated_at timestamptz NOT NULL,
    title text NOT NULL DEFAULT '',
    title_search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('simple', title)
    ) STORED,
    content_digest text NOT NULL CHECK (length(btrim(content_digest)) > 0),
    content_size_bytes bigint NOT NULL CHECK (content_size_bytes >= 0),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
        jsonb_typeof(metadata) = 'object'
    ),
    deleted_at timestamptz,
    purge_after timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, document_id),
    CHECK (
        (
            deleted_at IS NULL
            AND purge_after IS NULL
        )
        OR (
            deleted_at IS NOT NULL
            AND purge_after IS NOT NULL
            AND purge_after >= deleted_at
        )
    )
);

-- folder_sources
CREATE TABLE folder_sources (
    folder_id text PRIMARY KEY CHECK (length(btrim(folder_id)) > 0),
    tenant_id text NOT NULL
        REFERENCES tenant_storage_scopes (tenant_id)
        ON DELETE CASCADE,
    source_version text NOT NULL CHECK (length(btrim(source_version)) > 0),
    source_created_at timestamptz NOT NULL,
    source_updated_at timestamptz NOT NULL,
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    path text CHECK (
        path IS NULL OR length(btrim(path)) > 0
    ),
    parent_folder_id text CHECK (
        parent_folder_id IS NULL OR length(btrim(parent_folder_id)) > 0
    ),
    description text NOT NULL DEFAULT '',
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
        jsonb_typeof(metadata) = 'object'
    ),
    deleted_at timestamptz,
    purge_after timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (
        (
            deleted_at IS NULL
            AND purge_after IS NULL
        )
        OR (
            deleted_at IS NOT NULL
            AND purge_after IS NOT NULL
            AND purge_after >= deleted_at
        )
    )
);
