from __future__ import annotations

import unittest
from pathlib import Path


class PostgresMigrationTests(unittest.TestCase):
    def test_initial_migration_chain_is_split_by_storage_responsibility(self) -> None:
        migration_files = sorted(Path("migrations/versions").glob("20260513_*.py"))
        names = [path.name for path in migration_files]

        self.assertEqual(
            names,
            [
                "20260513_0001_create_profile_storage.py",
                "20260513_0002_create_task_storage.py",
            ],
        )

    def test_migrations_create_normalized_tables_without_legacy_paths(self) -> None:
        migrations = {
            path.name: path.read_text()
            for path in Path("migrations/versions").glob("20260513_*.py")
        }
        migration_text = "\n".join(migrations.values())
        profile_migration = migrations["20260513_0001_create_profile_storage.py"]

        self.assertIn("title text NOT NULL", profile_migration)
        self.assertNotIn("topics text[]", profile_migration)
        self.assertNotIn("main_topics text[]", profile_migration)
        self.assertNotIn("concepts text[]", profile_migration)
        self.assertNotIn("keywords text[]", profile_migration)
        self.assertNotIn("suggested_tags text[]", profile_migration)
        self.assertNotIn("document_profile_terms", profile_migration)
        self.assertNotIn("document_profile_folder_suggestions", profile_migration)
        self.assertNotIn("folder_suggestions", profile_migration)
        self.assertNotIn(
            "document_profile_items",
            profile_migration,
        )
        self.assertIn(
            "document_id text PRIMARY KEY",
            profile_migration,
        )
        self.assertIn("source_version text NOT NULL", profile_migration)
        self.assertIn("profile_schema_version text NOT NULL", profile_migration)
        self.assertIn("concepts_json jsonb NOT NULL", profile_migration)
        self.assertIn(
            "profile_confidence IS NULL",
            profile_migration,
        )
        self.assertIn("profile_confidence >= 0.0", profile_migration)
        self.assertIn("profile_confidence <= 1.0", profile_migration)
        self.assertNotIn("document_profiles_tenant_idx", profile_migration)
        self.assertNotIn("CREATE TABLE index_targets", profile_migration)
        self.assertNotIn("CREATE TABLE projection_state", profile_migration)
        self.assertIn("CREATE TABLE outbox_events", profile_migration)
        self.assertIn("DOCUMENT_INDEXED", profile_migration)
        self.assertIn("FOLDER_INDEXED", profile_migration)
        self.assertNotIn("CREATE TABLE index_state", profile_migration)
        self.assertIn("aggregate_id text NOT NULL", profile_migration)
        self.assertIn("sequence bigint GENERATED ALWAYS AS IDENTITY", profile_migration)
        self.assertIn("event_key text NOT NULL", profile_migration)
        self.assertIn(
            "event_key = aggregate_type || ':' || aggregate_id",
            profile_migration,
        )
        self.assertIn("outbox_events_aggregate_sequence_idx", profile_migration)
        self.assertIn("outbox_events_key_sequence_idx", profile_migration)
        self.assertIn("event_schema_version text NOT NULL", profile_migration)
        self.assertIn("payload jsonb NOT NULL", profile_migration)
        for projection_kind in (
            "qdrant_chunks",
            "qdrant_document_vector",
            "qdrant_folder_vector",
            "neo4j_document_relationships",
            "neo4j_document_concepts",
            "neo4j_folder_hierarchy",
            "neo4j_tag",
        ):
            self.assertNotIn(projection_kind, profile_migration)
        self.assertNotIn("qdrant_document',", profile_migration)
        self.assertNotIn("neo4j_document_graph", profile_migration)
        self.assertNotIn(
            "PRIMARY KEY (tenant, target_kind, document_type, document_id)",
            profile_migration,
        )
        self.assertNotIn("document_id text NOT NULL CHECK", profile_migration)
        self.assertNotIn("folder_id text PRIMARY KEY", profile_migration)
        self.assertNotIn(
            "PRIMARY KEY (tenant, document_type, document_id)",
            profile_migration,
        )
        self.assertNotIn(
            "PRIMARY KEY (tenant, folder_id)",
            profile_migration,
        )
        self.assertNotIn(
            "profile_id",
            profile_migration,
        )
        self.assertNotIn("folder_documents_ref_document_idx", profile_migration)
        self.assertNotIn("PRIMARY KEY (folder_id, document_id)", profile_migration)
        self.assertNotIn("representative_tags text[]", profile_migration)
        self.assertNotIn("folder_profile_terms", profile_migration)
        self.assertNotIn("representative_tag", profile_migration)
        self.assertNotIn("folder_profiles", profile_migration)
        self.assertNotIn("folder_documents_ref", profile_migration)
        self.assertNotIn("CREATE TABLE folder_documents (", profile_migration)
        self.assertNotIn("document_folder_refs", profile_migration)
        self.assertNotIn("document_profile_folders", profile_migration)
        self.assertNotIn("document_profile_topics", profile_migration)
        self.assertNotIn("document_profile_concepts", profile_migration)
        self.assertNotIn("document_profile_keywords", profile_migration)
        self.assertNotIn("document_profile_tag_suggestions", profile_migration)
        self.assertNotIn("document_profile_evidence_spans", profile_migration)
        self.assertNotIn("document_profile_chunk_mentions", profile_migration)
        self.assertNotIn("folder_profile_documents", profile_migration)
        self.assertNotIn("folder_profile_topics", profile_migration)
        self.assertNotIn("folder_profile_concepts", profile_migration)
        self.assertNotIn("folder_profile_keywords", profile_migration)
        self.assertNotIn("folder_profile_representative_tags", profile_migration)
        self.assertNotIn("folder_profile_representative_documents", profile_migration)
        self.assertNotIn("folder_profile_items", profile_migration)
        self.assertIn(
            "host_action_dependencies",
            migrations["20260513_0002_create_task_storage.py"],
        )
        self.assertIn(
            "task_id uuid PRIMARY KEY",
            migrations["20260513_0002_create_task_storage.py"],
        )
        self.assertIn(
            "request_text text NOT NULL",
            migrations["20260513_0002_create_task_storage.py"],
        )
        self.assertIn(
            "CREATE TABLE task_requests",
            migrations["20260513_0002_create_task_storage.py"],
        )
        self.assertIn(
            "task_request_id uuid PRIMARY KEY",
            migrations["20260513_0002_create_task_storage.py"],
        )
        self.assertIn(
            "output_id uuid PRIMARY KEY",
            migrations["20260513_0002_create_task_storage.py"],
        )
        self.assertIn(
            "action_id uuid PRIMARY KEY",
            migrations["20260513_0002_create_task_storage.py"],
        )
        self.assertIn(
            "event_id uuid PRIMARY KEY",
            migrations["20260513_0002_create_task_storage.py"],
        )
        self.assertIn(
            "tasks_current_action_id_fk",
            migrations["20260513_0002_create_task_storage.py"],
        )
        self.assertNotIn(
            "tasks_request_id_unique_idx",
            migrations["20260513_0002_create_task_storage.py"],
        )
        self.assertNotIn(
            "conversation_id text",
            migrations["20260513_0002_create_task_storage.py"],
        )
        self.assertNotIn(
            "tasks_tenant_idx",
            migrations["20260513_0002_create_task_storage.py"],
        )
        self.assertNotIn(
            "PRIMARY KEY (tenant, task_id)",
            migrations["20260513_0002_create_task_storage.py"],
        )
        self.assertNotIn(
            "FOREIGN KEY (tenant, task_id)",
            migrations["20260513_0002_create_task_storage.py"],
        )
        self.assertNotIn("_legacy", migration_text)
        self.assertNotIn("backfill", migration_text.casefold())
        self.assertNotIn("profile_json", migration_text)
        self.assertNotIn("snapshot_json", migration_text)
        self.assertNotIn("event_json", migration_text)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS", migration_text)
        self.assertNotIn("CREATE INDEX IF NOT EXISTS", migration_text)
        self.assertNotIn("foldmind_", migration_text)


if __name__ == "__main__":
    unittest.main()
