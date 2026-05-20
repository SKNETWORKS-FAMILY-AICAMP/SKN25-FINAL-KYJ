-- This file is executed by its Alembic revision. Keep statements in dependency order.

-- source_document_folder_relations
CREATE TABLE source_document_folder_relations (
    tenant_id text NOT NULL,
    document_id text NOT NULL,
    folder_id text NOT NULL CHECK (length(btrim(folder_id)) > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, document_id, folder_id),
    FOREIGN KEY (tenant_id, document_id)
        REFERENCES document_sources (tenant_id, document_id)
        ON DELETE CASCADE
);
