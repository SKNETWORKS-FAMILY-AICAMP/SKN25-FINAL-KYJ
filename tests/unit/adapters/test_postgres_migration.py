from __future__ import annotations

import unittest
from pathlib import Path


def read_revision_with_sql_files(path: Path) -> str:
    sql_dir = Path("migrations/sql") / path.stem
    sql_text = "\n".join(
        sql_path.read_text(encoding="utf-8")
        for sql_path in sorted(sql_dir.glob("*.sql"))
    )
    return f"{path.read_text(encoding='utf-8')}\n{sql_text}"


class PostgresMigrationTests(unittest.TestCase):
    def test_initial_migration_chain_is_split_by_storage_responsibility(self) -> None:
        migration_files = sorted(Path("migrations/versions").glob("20260513_*.py"))
        names = [path.name for path in migration_files]

        self.assertEqual(
            names,
            [
                "20260513_0001_create_projection_storage.py",
                "20260513_0002_create_task_storage.py",
            ],
        )

    def test_initial_schema_matches_projection_storage_contract(self) -> None:
        migrations = {
            path.name: read_revision_with_sql_files(path)
            for path in Path("migrations/versions").glob("20260513_*.py")
        }
        schema = migrations["20260513_0001_create_projection_storage.py"]
        workflow_schema = migrations["20260513_0002_create_task_storage.py"]
        all_schema = "\n".join(migrations.values())
        normalized_schema = " ".join(schema.split())

        for table_name in (
            "tenant_storage_scopes",
            "document_sources",
            "source_document_folder_relation",
            "folder_sources",
            "document_index_records",
            "document_chunks",
            "document_signals",
            "folder_index_records",
            "folder_signals",
            "vector_projection_records",
            "outbox_events",
        ):
            self.assertIn(f"CREATE TABLE {table_name}", schema)

        for removed_table in (
            "tenant_vector_migrations",
            "document_vector_projections",
            "chunk_vector_projections",
            "signal_vector_projections",
            "folder_vector_projections",
            "indexing_work_items",
            "generated_artifacts",
            "agent_executions",
            "agent_tool_calls",
            "action_plans",
            "action_plan_items",
            "failure_logs",
            "retrieval_runs",
            "retrieval_results",
            "source_document_folder_relations",
        ):
            self.assertNotIn(f"CREATE TABLE {removed_table}", schema)

        self.assertIn("document_id text PRIMARY KEY", schema)
        self.assertIn("folder_id text PRIMARY KEY", schema)
        self.assertIn(
            "tenant_id text NOT NULL\n        REFERENCES tenant_storage_scopes (tenant_id)\n        ON DELETE CASCADE",
            schema,
        )
        self.assertIn(
            "document_type text CHECK (\n        document_type IS NULL",
            schema,
        )
        self.assertNotIn("latest_source_version", schema)
        self.assertNotIn("last_seen_at", schema)
        self.assertNotIn("document_refs", schema)
        self.assertNotIn("folder_refs", schema)
        self.assertNotIn("source_document_snapshots", schema)
        self.assertNotIn("source_folder_snapshots", schema)
        self.assertNotIn("document_ref_id", schema)
        self.assertNotIn("folder_ref_id", schema)
        self.assertNotIn("source_document_snapshot_id", schema)
        self.assertNotIn("source_folder_snapshot_id", schema)
        self.assertNotIn("is_current", schema)
        self.assertNotIn("superseded_at", schema)
        self.assertNotIn("UNIQUE (tenant_id, document_type, document_id)", schema)
        self.assertIn("UNIQUE (tenant_id, document_id)", schema)
        self.assertNotIn(
            "UNIQUE (tenant_id, document_ref_id, document_type, document_id)",
            schema,
        )
        tenant_state_schema = schema[
            schema.index("CREATE TABLE tenant_storage_scopes"):
            schema.index("CREATE TABLE document_sources")
        ]
        self.assertNotIn("metadata", tenant_state_schema)
        document_source_schema = schema[
            schema.index("CREATE TABLE document_sources"):
            schema.index("CREATE TABLE source_document_folder_relation")
        ]
        document_folder_relation_schema = schema[
            schema.index("CREATE TABLE source_document_folder_relation"):
            schema.index("CREATE TABLE folder_sources")
        ]
        folder_source_schema = schema[
            schema.index("CREATE TABLE folder_sources"):
            schema.index("CREATE TABLE document_index_records")
        ]
        document_index_schema = schema[
            schema.index("CREATE TABLE document_index_records"):
            schema.index("CREATE TABLE document_chunks")
        ]
        document_chunk_schema = schema[
            schema.index("CREATE TABLE document_chunks"):
            schema.index("CREATE TABLE document_signals")
        ]
        document_signal_schema = schema[
            schema.index("CREATE TABLE document_signals"):
            schema.index("CREATE TABLE folder_index_records")
        ]
        folder_index_schema = schema[
            schema.index("CREATE TABLE folder_index_records"):
            schema.index("CREATE TABLE folder_signals")
        ]
        folder_signal_schema = schema[
            schema.index("CREATE TABLE folder_signals"):
            schema.index("CREATE TABLE vector_projection_records")
        ]
        self.assertIn("title text NOT NULL DEFAULT ''", document_source_schema)
        self.assertIn("source_created_at timestamptz NOT NULL", document_source_schema)
        self.assertIn("source_updated_at timestamptz NOT NULL", document_source_schema)
        self.assertNotIn("folder_ids", document_source_schema)
        self.assertIn("folder_ids text[] NOT NULL", document_folder_relation_schema)
        self.assertIn("PRIMARY KEY (tenant_id, document_id)", document_folder_relation_schema)
        self.assertIn(
            "FOREIGN KEY (tenant_id, document_id)",
            document_folder_relation_schema,
        )
        self.assertIn(
            "REFERENCES document_sources (tenant_id, document_id)",
            document_folder_relation_schema,
        )
        self.assertIn(
            "array_position(folder_ids, NULL) IS NULL",
            document_folder_relation_schema,
        )
        self.assertNotIn("REFERENCES folder_sources", document_folder_relation_schema)
        self.assertNotIn("tag_ids", document_source_schema)
        self.assertIn("content_digest text NOT NULL", document_source_schema)
        self.assertIn("content_size_bytes bigint NOT NULL", document_source_schema)
        self.assertIn("name text NOT NULL", folder_source_schema)
        self.assertIn("source_created_at timestamptz NOT NULL", folder_source_schema)
        self.assertIn("source_updated_at timestamptz NOT NULL", folder_source_schema)
        self.assertIn("path text CHECK", folder_source_schema)
        self.assertIn("parent_folder_id text CHECK", folder_source_schema)
        self.assertIn("description text NOT NULL DEFAULT ''", folder_source_schema)
        self.assertNotIn("snapshot_digest", folder_source_schema)
        self.assertNotIn("snapshot_size_bytes", folder_source_schema)
        self.assertNotIn("title text", document_index_schema)
        self.assertNotIn("metadata jsonb", document_index_schema)
        self.assertNotIn("indexed_at", document_index_schema)
        self.assertNotIn("metadata jsonb", document_chunk_schema)
        self.assertNotIn("metadata jsonb", document_signal_schema)
        self.assertNotIn("metadata jsonb", folder_index_schema)
        self.assertNotIn("indexed_at", folder_index_schema)
        self.assertNotIn("metadata jsonb", folder_signal_schema)
        self.assertNotIn("indexed_snapshot_digest", folder_index_schema)
        self.assertNotIn("index_schema_version", folder_index_schema)
        self.assertIn("signal_set_version text NOT NULL DEFAULT '1'", folder_index_schema)
        self.assertIn("attributes_json jsonb NOT NULL", folder_signal_schema)
        self.assertNotIn("payload_json", folder_signal_schema)
        self.assertNotIn("score double precision", folder_signal_schema)
        self.assertIn("related_document_id text", folder_signal_schema)
        self.assertNotIn("CREATE TABLE vector_collections", schema)
        self.assertNotIn("CREATE TABLE tenant_vector_collection_bindings", schema)
        self.assertNotIn("prompt_version", document_index_schema)
        for removed_source_column in (
            "storage_uri",
            "encryption_key_ref",
            "status text",
            "purged_at",
            "error_code",
            "error_message",
        ):
            self.assertNotIn(removed_source_column, document_source_schema)
            self.assertNotIn(removed_source_column, folder_source_schema)
        self.assertNotIn("UNIQUE (tenant_id, folder_id)", schema)
        self.assertIn("document_id text PRIMARY KEY\n        REFERENCES document_sources", schema)
        self.assertIn("folder_id text PRIMARY KEY\n        REFERENCES folder_sources", schema)
        self.assertIn("UNIQUE (document_id, chunk_index)", schema)
        self.assertNotIn("FOREIGN KEY (chunk_id)", schema)
        self.assertNotIn("REFERENCES document_chunks (chunk_id)", schema)
        self.assertNotIn("FOREIGN KEY (tenant_id, chunk_id)", schema)
        self.assertIn("signal_id text PRIMARY KEY", schema)
        self.assertNotIn("PRIMARY KEY (tenant_id, signal_id)", schema)
        self.assertNotIn("UNIQUE (tenant_id, signal_id)", schema)
        self.assertNotIn("knowledge_signals", schema)
        self.assertNotIn("scope_type", schema)
        self.assertNotIn("scope_id", schema)
        self.assertNotIn("workspace", schema)
        vector_projection_schema = schema[
            schema.index("CREATE TABLE vector_projection_records"):
            schema.index("CREATE TABLE outbox_events")
        ]
        self.assertNotIn("vector_projection_id", vector_projection_schema)
        self.assertNotIn("aggregate_kind", vector_projection_schema)
        self.assertNotIn("aggregate_id", vector_projection_schema)
        self.assertNotIn("subject_id", vector_projection_schema)
        self.assertNotIn("source_version", vector_projection_schema)
        self.assertNotIn("payload_digest", vector_projection_schema)
        self.assertNotIn("projected_at", vector_projection_schema)
        self.assertNotIn("deleted_at", vector_projection_schema)
        self.assertNotIn("purge_after", vector_projection_schema)
        self.assertIn("source_kind text NOT NULL", vector_projection_schema)
        self.assertIn("source_id text NOT NULL", vector_projection_schema)
        self.assertIn("vector_item_kind text NOT NULL", vector_projection_schema)
        self.assertIn("vector_item_id text NOT NULL", vector_projection_schema)
        self.assertIn("PRIMARY KEY (collection_name, point_id)", vector_projection_schema)
        self.assertIn(
            "tenant_id,\n        collection_name,\n        source_kind,\n        source_id,\n        vector_item_kind,\n        vector_item_id",
            vector_projection_schema,
        )
        self.assertNotIn("UNIQUE (collection_name, point_id)", schema)
        self.assertNotIn("UNIQUE (tenant_id, collection_name, point_id)", schema)
        self.assertNotIn("FOREIGN KEY (collection_name, vector_item_kind)", vector_projection_schema)
        self.assertNotIn("FOREIGN KEY (collection_name, vector_kind)", vector_projection_schema)
        self.assertNotIn(
            "FOREIGN KEY (tenant_id, vector_kind, collection_name)",
            vector_projection_schema,
        )
        self.assertNotIn("tenant_vector_collection_bindings", vector_projection_schema)
        self.assertIn(
            "source_kind = 'document'\n            AND vector_item_kind IN ('document', 'chunk', 'signal')",
            vector_projection_schema,
        )
        self.assertIn(
            "source_kind = 'folder'\n            AND vector_item_kind IN ('folder', 'signal')",
            vector_projection_schema,
        )
        self.assertIn(
            "vector_item_kind IN ('document', 'folder')\n            AND vector_item_id = source_id",
            vector_projection_schema,
        )
        self.assertNotIn("REFERENCES document_index_records", vector_projection_schema)
        self.assertNotIn("REFERENCES document_chunks", vector_projection_schema)
        self.assertNotIn("REFERENCES document_signals", vector_projection_schema)
        self.assertNotIn("REFERENCES folder_signals", vector_projection_schema)
        self.assertNotIn("REFERENCES folder_index_records", vector_projection_schema)
        self.assertNotIn("status text", vector_projection_schema)
        self.assertIn("vector_projection_source_idx", schema)
        self.assertIn("source_document_folder_relation_tenant_updated_idx", schema)
        self.assertIn("document_index_records_retention_idx", schema)
        self.assertNotIn("document_chunks_document_idx", schema)
        self.assertNotIn("vector_projection_aggregate_idx", schema)
        self.assertNotIn("vector_projection_retention_idx", schema)
        self.assertNotIn("tenant_vector_active_binding_uidx", schema)
        self.assertNotIn("tenant_vector_bindings_role_idx", schema)
        self.assertNotIn("WHERE deprecated_at IS NULL", schema)
        self.assertIn("'signal'", schema)
        self.assertNotIn("graph_node_projections", schema)
        self.assertNotIn("neo4j_node_id", schema)
        self.assertNotIn("graph_projection_records", schema)
        self.assertNotIn("graph_projection_status_idx", schema)
        self.assertIn("event_id uuid PRIMARY KEY", schema)
        self.assertIn("'DOCUMENT_FOLDER_RELATIONS_INDEXED'", schema)
        self.assertIn("event_sequence bigint GENERATED ALWAYS AS IDENTITY", schema)
        self.assertIn("source_kind text NOT NULL", schema)
        self.assertIn("source_id text NOT NULL", schema)
        self.assertIn("partition_key text GENERATED ALWAYS AS", schema)
        self.assertIn("payload_schema_version smallint NOT NULL DEFAULT 1", schema)
        self.assertNotIn("aggregate_type text", schema)
        self.assertNotIn("aggregate_id text", schema)
        self.assertNotIn("event_key text", schema)
        self.assertNotIn("event_schema_version", schema)
        self.assertIn("UNIQUE (tenant_id, idempotency_key)", schema)
        self.assertNotIn("retain_until timestamptz,\n    created_at", schema)
        self.assertIn("outbox_events_source_sequence_idx", schema)
        self.assertIn("outbox_events_partition_sequence_idx", schema)
        self.assertNotIn("outbox_events_aggregate_sequence_idx", schema)
        self.assertNotIn("outbox_events_key_sequence_idx", schema)
        self.assertNotIn("outbox_events_retention_idx", schema)
        self.assertNotIn("retrieval_runs_tenant_started_idx", schema)
        self.assertNotIn("indexing_work_items_status_idx", schema)
        self.assertNotIn("generated_artifacts_purge_idx", schema)
        self.assertNotIn("agent_executions_tenant_started_idx", schema)
        self.assertNotIn("action_plans_tenant_status_idx", schema)
        self.assertNotIn("failure_logs_tenant_created_idx", schema)
        self.assertIn("CREATE EXTENSION IF NOT EXISTS moddatetime", schema)
        self.assertIn("EXECUTE FUNCTION moddatetime(updated_at)", schema)

        for forbidden in (
            "app_document_id",
            "app_folder_id",
            "outbox_event_deliveries",
            "outbox_event_attempts",
            "indexing_tasks",
            "locked_by",
            "lease_token",
            "lock_expires_at",
            "available_at",
            "indexing_work_items_poll_idx",
            "indexing_work_items_lease_idx",
            "concepts_json",
            "document_profiles",
            "folder_profiles",
            "_legacy",
            "backfill",
            "CREATE TABLE IF NOT EXISTS",
            "CREATE INDEX IF NOT EXISTS",
            "CREATE OR REPLACE FUNCTION set_updated_at",
            "EXECUTE FUNCTION set_updated_at",
        ):
            self.assertNotIn(forbidden, all_schema)

        for table_name in (
            "tasks",
            "task_inputs",
            "task_jobs",
            "task_job_results",
            "host_actions",
            "task_events",
        ):
            self.assertIn(f"CREATE TABLE {table_name}", workflow_schema)
        for removed_workflow_table in (
            "task_requests",
            "task_outputs",
        ):
            self.assertNotIn(f"CREATE TABLE {removed_workflow_table}", workflow_schema)

        self.assertIn("task_id uuid PRIMARY KEY", workflow_schema)
        self.assertIn(
            "tenant text NOT NULL\n        REFERENCES tenant_storage_scopes (tenant_id)\n        ON DELETE CASCADE",
            workflow_schema,
        )
        self.assertIn("request_text text NOT NULL", workflow_schema)
        self.assertIn("context_json jsonb NOT NULL", workflow_schema)
        self.assertNotIn("context_json->'requested_at'", workflow_schema)
        self.assertIn("task_input_id uuid PRIMARY KEY", workflow_schema)
        self.assertIn("input_text text NOT NULL", workflow_schema)
        self.assertIn("deleted_at timestamptz", workflow_schema)
        self.assertNotIn("removed_at", workflow_schema)
        self.assertIn("job_id uuid PRIMARY KEY", workflow_schema)
        self.assertIn("round_index integer NOT NULL", workflow_schema)
        self.assertIn("job_result_id uuid PRIMARY KEY", workflow_schema)
        self.assertIn("summary_json jsonb NOT NULL", workflow_schema)
        self.assertIn("result_type text CHECK", workflow_schema)
        self.assertIn("result_json jsonb CHECK", workflow_schema)
        self.assertIn("job_id uuid,", workflow_schema)
        self.assertIn("tasks_current_action_id_fk", workflow_schema)
        self.assertIn("FOREIGN KEY (task_id, current_action_id)", workflow_schema)
        self.assertNotIn("FOREIGN KEY (current_action_id)", workflow_schema)
        self.assertIn("UNIQUE (task_id, position)", workflow_schema)
        self.assertIn("UNIQUE (task_id, job_id)", workflow_schema)
        self.assertIn("UNIQUE (task_id, round_index, position)", workflow_schema)
        self.assertIn("UNIQUE (job_id, position)", workflow_schema)
        self.assertIn("FOREIGN KEY (task_id, job_id)", workflow_schema)
        self.assertIn("ON DELETE SET NULL (job_id)", workflow_schema)
        self.assertIn("completed_at IS NULL", workflow_schema)
        self.assertIn("status = 'failed'", workflow_schema)
        self.assertIn("AND error_json IS NOT NULL", workflow_schema)
        host_action_schema = workflow_schema[
            workflow_schema.index("CREATE TABLE host_actions"):
            workflow_schema.index("-- tasks_current_action_id_fk")
        ]
        self.assertNotIn("result_json", host_action_schema)
        self.assertNotIn("CREATE TABLE host_action_dependencies", workflow_schema)


if __name__ == "__main__":
    unittest.main()
