-- This file is executed by its Alembic revision. Keep statements in dependency order.

-- tenant_storage_scopes_purge_idx
CREATE INDEX tenant_storage_scopes_purge_idx
    ON tenant_storage_scopes (purge_after)
    WHERE deleted_at IS NOT NULL;

-- document_sources_tenant_updated_idx
CREATE INDEX document_sources_tenant_updated_idx
    ON document_sources (tenant_id, updated_at DESC);

-- document_sources_purge_idx
CREATE INDEX document_sources_purge_idx
    ON document_sources (purge_after)
    WHERE deleted_at IS NOT NULL;

-- source_document_folder_relations_folder_idx
CREATE INDEX source_document_folder_relations_folder_idx
    ON source_document_folder_relations (tenant_id, folder_id);

-- document_chunks_input_digest_idx
CREATE INDEX document_chunks_input_digest_idx
    ON document_chunks (tenant_id, document_id, index_input_digest);

-- document_chunks_document_order_idx
CREATE INDEX document_chunks_document_order_idx
    ON document_chunks (tenant_id, document_id, chunk_index);

-- document_chunks_search_idx
CREATE INDEX document_chunks_search_idx
    ON document_chunks USING gin (search_vector);

-- folder_sources_tenant_updated_idx
CREATE INDEX folder_sources_tenant_updated_idx
    ON folder_sources (tenant_id, updated_at DESC);

-- folder_sources_purge_idx
CREATE INDEX folder_sources_purge_idx
    ON folder_sources (purge_after)
    WHERE deleted_at IS NOT NULL;

-- document_signals_document_type_idx
CREATE INDEX document_signals_document_type_idx
    ON document_signals (document_id, signal_type);

-- document_signals_type_key_idx
CREATE INDEX document_signals_type_key_idx
    ON document_signals (signal_type, signal_key);

-- document_signals_input_digest_idx
CREATE INDEX document_signals_input_digest_idx
    ON document_signals (document_id, index_input_digest);

-- folder_signals_folder_type_idx
CREATE INDEX folder_signals_folder_type_idx
    ON folder_signals (folder_id, signal_type);

-- folder_signals_input_digest_idx
CREATE INDEX folder_signals_input_digest_idx
    ON folder_signals (folder_id, index_input_digest);

-- folder_signals_related_document_idx
CREATE INDEX folder_signals_related_document_idx
    ON folder_signals (related_document_id)
    WHERE related_document_id IS NOT NULL;

-- document_index_records_retention_idx
CREATE INDEX document_index_records_retention_idx
    ON document_index_records (purge_after)
    WHERE deleted_at IS NOT NULL;

-- folder_index_records_retention_idx
CREATE INDEX folder_index_records_retention_idx
    ON folder_index_records (purge_after)
    WHERE deleted_at IS NOT NULL;

-- vector_projection_source_idx
CREATE INDEX vector_projection_source_idx
    ON vector_projection_records (
        tenant_id,
        source_kind,
        source_id,
        vector_item_kind
    );

-- vector_projection_input_digest_idx
CREATE INDEX vector_projection_input_digest_idx
    ON vector_projection_records (
        tenant_id,
        source_kind,
        source_id,
        vector_item_kind,
        index_input_digest
    );

-- outbox_events_source_sequence_idx
CREATE INDEX outbox_events_source_sequence_idx
    ON outbox_events (tenant_id, source_kind, source_id, event_sequence DESC);

-- outbox_events_partition_sequence_idx
CREATE INDEX outbox_events_partition_sequence_idx
    ON outbox_events (partition_key, event_sequence DESC);
