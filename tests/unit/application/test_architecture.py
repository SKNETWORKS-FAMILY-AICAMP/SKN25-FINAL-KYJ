from __future__ import annotations

import unittest
from pathlib import Path

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "src").exists()
)
PACKAGE_ROOT = PROJECT_ROOT / "src" / "foldmind_ai_core"


def python_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
    ]


class ArchitectureTests(unittest.TestCase):
    def assert_files_do_not_contain(self, root: Path, forbidden: tuple[str, ...]) -> None:
        for path in python_files(root):
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"{path} must not import {token}")

    def test_domain_does_not_depend_on_outer_layers(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "domain",
            (
                "foldmind_ai_core.application",
                "foldmind_ai_core.adapters",
                "foldmind_ai_core.infrastructure",
                "fastapi",
                "langgraph",
                "qdrant_client",
                "psycopg",
                "from neo4j",
            ),
        )

    def test_shared_does_not_depend_on_core_or_outer_layers(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "shared",
            (
                "foldmind_ai_core.domain",
                "foldmind_ai_core.application",
                "foldmind_ai_core.adapters",
                "foldmind_ai_core.infrastructure",
                "foldmind_ai_core.bootstrap",
                "fastapi",
                "langgraph",
            ),
        )

    def test_application_does_not_depend_on_adapters_or_frameworks(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "application",
            (
                "foldmind_ai_core.adapters",
                "foldmind_ai_core.infrastructure",
                "fastapi",
                "langgraph",
                "qdrant_client",
                "psycopg",
                "from neo4j",
            ),
        )

    def test_application_ports_are_boundary_protocols(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "application" / "ports",
            (
                "foldmind_ai_core.application.use_cases",
                "foldmind_ai_core.application.agents",
                "foldmind_ai_core.application.workflows",
                "foldmind_ai_core.adapters",
                "foldmind_ai_core.infrastructure",
                "foldmind_ai_core.bootstrap",
                "fastapi",
                "langgraph",
            ),
        )

    def test_application_internals_do_not_depend_on_inbound_ports(self) -> None:
        for path in python_files(PACKAGE_ROOT / "application"):
            if "ports" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "foldmind_ai_core.application.ports.inbound",
                text,
                f"{path} must not depend on inbound ports",
            )

    def test_indexing_application_does_not_leak_database_transaction_handles(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "application",
            (
                "conn: Any",
                "AbstractContextManager[Any]",
                "upsert_with_connection",
                "delete_with_connection",
                "append(event, *, conn",
                "TransactionManager",
                "OutboxRepository",
            ),
        )

    def test_indexing_versions_are_not_hidden_behind_fake_defaults(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT,
            (
                "configured-embedding",
                "configured-llm",
                "default-v1",
                "20260514_0001",
                "DocumentChunkingConfig()",
                "profile-v1",
                "document-profiling-v1",
                'source_version: str = "1"',
                'source_version: str = "1",',
                'or "1"',
            ),
        )

    def test_dead_graph_and_storage_layers_are_not_reintroduced(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT,
            (
                "class GraphNodeType",
                "class GraphNode",
                "class DocumentRefNode",
                "class FolderRefNode",
                "class TagNode",
                "class ConceptNode",
                "class GraphEdge",
                "class GraphPath",
                "GraphProjection",
                "node_id",
                "node_type",
                "HAS_CHUNK",
                "_merge_edge",
                "safe_relation_type",
                "edge_id",
                "relation_type",
                "IndexStore",
                "KnowledgeGraphStore",
            ),
        )

    def test_domain_outbox_does_not_own_transport_codec(self) -> None:
        text = (PACKAGE_ROOT / "domain" / "indexing" / "outbox.py").read_text(
            encoding="utf-8"
        )
        for token in (
            "kafka_key",
            "source_document_payload",
            "source_document_from_payload",
            "source_folder_payload",
            "source_folder_from_payload",
            "document_chunk_payload",
            "document_chunk_from_payload",
            "document_profile_payload",
            "document_profile_from_payload",
        ):
            self.assertNotIn(token, text)

    def test_qdrant_repositories_do_not_expose_capability_flags(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "adapters" / "outbound" / "qdrant",
            ("supports_keyword_search", "supports_document_search", "supports_"),
        )

    def test_application_orchestrators_depend_on_ports_not_concrete_use_cases(self) -> None:
        forbidden = ("foldmind_ai_core.application.use_cases",)
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "application" / "workflows",
            forbidden,
        )
        for path in python_files(PACKAGE_ROOT / "application" / "use_cases"):
            if path.name == "__init__.py":
                continue
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"{path} must depend on a port instead")

    def test_application_workflows_do_not_contain_runtime_adapter_state(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "application" / "workflows",
            (
                "GraphState",
                "WorkflowCheckpointState",
                "langgraph",
                "foldmind_ai_core.adapters",
                "foldmind_ai_core.infrastructure",
                "fastapi",
            ),
        )

    def test_workflow_runtime_adapter_stays_outbound_only(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "adapters" / "outbound" / "workflow_runtime",
            (
                "foldmind_ai_core.application.ports.inbound",
                "foldmind_ai_core.application.use_cases",
                "foldmind_ai_core.adapters.inbound",
                "foldmind_ai_core.bootstrap",
                "fastapi",
            ),
        )

    def test_workflow_artifact_store_hides_generic_artifact_access(self) -> None:
        from foldmind_ai_core.application.workflows.artifacts.store import (
            WorkflowArtifactStore,
        )

        public_methods = {
            name for name in dir(WorkflowArtifactStore)
            if not name.startswith("_")
        }

        self.assertIn("record_step_outcome", public_methods)
        self.assertFalse(
            {"get", "get_list", "set", "append_output"} & public_methods,
            "Workflow artifact access should be exposed through typed methods.",
        )

    def test_inbound_http_and_app_factory_depend_on_inbound_ports(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "adapters" / "inbound" / "http",
            (
                "foldmind_ai_core.application.use_cases",
                "foldmind_ai_core.application.agents",
                "foldmind_ai_core.application.workflows",
                "foldmind_ai_core.application.ports.outbound",
                "foldmind_ai_core.adapters.outbound",
                "foldmind_ai_core.infrastructure",
                "foldmind_ai_core.bootstrap",
                "langgraph",
            ),
        )
        app_factory = PACKAGE_ROOT / "bootstrap" / "app_factory.py"
        self.assertNotIn(
            "foldmind_ai_core.application.use_cases",
            app_factory.read_text(encoding="utf-8"),
        )

    def test_inbound_messaging_depends_on_ports_and_domain_not_application_internals(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "adapters" / "inbound" / "messaging",
            (
                "foldmind_ai_core.application.services",
                "foldmind_ai_core.application.use_cases",
                "foldmind_ai_core.application.agents",
                "foldmind_ai_core.application.workflows",
                "foldmind_ai_core.application.ports.outbound",
                "foldmind_ai_core.adapters.outbound",
                "foldmind_ai_core.bootstrap",
                "foldmind_ai_core.workers",
                "OutboxMessageProcessor",
                "OutboxWorkerRuntime",
                "DlqProducer",
                "KafkaDlqProducer",
                "fastapi",
                "langgraph",
            ),
        )
        messaging_runtime = PACKAGE_ROOT / "adapters" / "inbound" / "messaging" / "runtime.py"
        self.assertFalse(messaging_runtime.exists())
        kafka_package = PACKAGE_ROOT / "adapters" / "inbound" / "kafka"
        self.assertFalse((kafka_package / "__init__.py").exists())
        self.assertFalse(list(kafka_package.glob("*.py")))

    def test_outbound_adapters_do_not_depend_on_inbound_side(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "adapters" / "outbound",
            (
                "foldmind_ai_core.application.ports.inbound",
                "foldmind_ai_core.application.use_cases",
                "foldmind_ai_core.adapters.inbound",
                "foldmind_ai_core.bootstrap",
                "fastapi",
            ),
        )

    def test_old_ai_core_package_is_removed(self) -> None:
        self.assertFalse((PROJECT_ROOT / "src" / "ai_core").exists())
        self.assert_files_do_not_contain(PACKAGE_ROOT, ("import ai_core", "from ai_core"))

    def test_infrastructure_package_is_removed(self) -> None:
        self.assertFalse((PACKAGE_ROOT / "infrastructure").exists())

    def test_outbound_adapter_packages_do_not_keep_dead_alias_layers(self) -> None:
        outbound = PACKAGE_ROOT / "adapters" / "outbound"
        for package_name in (
            "checkpoint",
            "embedding",
            "graph_store",
            "llm",
            "observability",
            "ontology_reasoner",
            "tokenizer",
            "vector_store",
            "workflow_store",
        ):
            package_path = outbound / package_name
            self.assertFalse((package_path / "__init__.py").exists())
            self.assertFalse(list(package_path.glob("*.py")))

    def test_test_tree_does_not_keep_old_storage_placeholder_packages(self) -> None:
        integration = PROJECT_ROOT / "tests" / "integration"
        for package_name in (
            "graph_store",
            "ontology_reasoner",
            "vector_store",
            "workflow_store",
        ):
            package_path = integration / package_name
            self.assertFalse((package_path / "__init__.py").exists())
            self.assertFalse(list(package_path.glob("*.py")))
