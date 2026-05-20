-- This file is executed by its Alembic revision. Keep statements in dependency order.

-- vector_projection_records
CREATE TABLE vector_projection_records (
    tenant_id text NOT NULL
        REFERENCES tenant_storage_scopes (tenant_id)
        ON DELETE CASCADE,
    collection_name text NOT NULL CHECK (
        length(btrim(collection_name)) > 0
    ),
    point_id uuid NOT NULL,
    source_kind text NOT NULL CHECK (
        source_kind IN ('document', 'folder')
    ),
    source_id text NOT NULL CHECK (length(btrim(source_id)) > 0),
    vector_item_kind text NOT NULL CHECK (
        vector_item_kind IN ('document', 'chunk', 'signal', 'folder')
    ),
    vector_item_id text NOT NULL CHECK (length(btrim(vector_item_id)) > 0),
    index_input_digest text NOT NULL CHECK (
        length(btrim(index_input_digest)) > 0
    ),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (collection_name, point_id),
    UNIQUE (
        tenant_id,
        collection_name,
        source_kind,
        source_id,
        vector_item_kind,
        vector_item_id
    ),
    CHECK (
        (
            source_kind = 'document'
            AND vector_item_kind IN ('document', 'chunk', 'signal')
        )
        OR (
            source_kind = 'folder'
            AND vector_item_kind IN ('folder', 'signal')
        )
    ),
    CHECK (
        (
            vector_item_kind IN ('document', 'folder')
            AND vector_item_id = source_id
        )
        OR vector_item_kind IN ('chunk', 'signal')
    )
);
