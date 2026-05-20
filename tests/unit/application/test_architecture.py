from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any, cast

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

    def test_core_owns_application_and_domain_packages(self) -> None:
        self.assertTrue((PACKAGE_ROOT / "core" / "application").is_dir())
        self.assertTrue((PACKAGE_ROOT / "core" / "domain").is_dir())
        self.assertFalse((PACKAGE_ROOT / "application").exists())
        self.assertFalse((PACKAGE_ROOT / "domain").exists())

    def test_domain_is_split_into_models_and_services(self) -> None:
        domain_root = PACKAGE_ROOT / "core" / "domain"
        self.assertTrue((domain_root / "models").is_dir())
        self.assertTrue((domain_root / "services").is_dir())
        self.assertEqual(
            {
                path.name
                for path in domain_root.iterdir()
                if path.is_dir() and path.name != "__pycache__"
            },
            {"models", "services"},
        )

    def test_domain_models_do_not_hide_domain_services(self) -> None:
        for path in python_files(PACKAGE_ROOT / "core" / "domain" / "models"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("\ndef ", text, f"{path} must keep rules in domain services.")
            self.assertNotIn(
                "InvalidInputError",
                text,
                f"{path} must delegate validation rules to domain services.",
            )

    def test_domain_services_do_not_depend_on_outer_layers(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "core" / "domain" / "services",
            (
                "foldmind_ai_core.core.application",
                "foldmind_ai_core.adapters",
                "foldmind_ai_core.infrastructure",
                "fastapi",
                "langgraph",
                "qdrant_client",
                "psycopg",
                "from neo4j",
            ),
        )

    def test_domain_profiling_does_not_parse_agent_payloads(self) -> None:
        text = (
            PACKAGE_ROOT
            / "core"
            / "domain"
            / "services"
            / "profiling.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("extracted_payload", text)
        self.assertNotIn("signal_evidence_from_payload", text)

    def test_domain_services_are_not_left_in_application_services(self) -> None:
        application_services = PACKAGE_ROOT / "core" / "application" / "services"
        workflow_use_cases = PACKAGE_ROOT / "core" / "application" / "use_cases" / "workflow"
        domain_services = PACKAGE_ROOT / "core" / "domain" / "services"
        for retired_application_module in (
            "document_chunker.py",
            "workflow_request_queue.py",
        ):
            self.assertFalse((application_services / retired_application_module).exists())
        self.assertFalse((workflow_use_cases / "_task_state.py").exists())
        for domain_service_module in (
            "document_chunking.py",
            "workflow_inputs.py",
            "indexing.py",
            "workflow.py",
        ):
            self.assertTrue((domain_services / domain_service_module).is_file())

    def test_domain_does_not_depend_on_outer_layers(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "core" / "domain",
            (
                "foldmind_ai_core.core.application",
                "foldmind_ai_core.adapters",
                "foldmind_ai_core.infrastructure",
                "fastapi",
                "langgraph",
                "qdrant_client",
                "psycopg",
                "from neo4j",
            ),
        )

    def test_domain_tests_do_not_depend_on_application_layer(self) -> None:
        self.assert_files_do_not_contain(
            PROJECT_ROOT / "tests" / "unit" / "domain",
            ("foldmind_ai_core.core.application",),
        )

    def test_shared_does_not_depend_on_core_or_outer_layers(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "shared",
            (
                "foldmind_ai_core.core.domain",
                "foldmind_ai_core.core.application",
                "foldmind_ai_core.adapters",
                "foldmind_ai_core.infrastructure",
                "foldmind_ai_core.bootstrap",
                "fastapi",
                "langgraph",
            ),
        )

    def test_application_does_not_depend_on_adapters_or_frameworks(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "core" / "application",
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
            PACKAGE_ROOT / "core" / "application" / "ports",
            (
                "foldmind_ai_core.core.application.use_cases",
                "foldmind_ai_core.core.application.agents",
                "foldmind_ai_core.core.application.workflows",
                "foldmind_ai_core.adapters",
                "foldmind_ai_core.infrastructure",
                "foldmind_ai_core.bootstrap",
                "fastapi",
                "langgraph",
            ),
        )

    def test_application_capabilities_are_not_hidden_under_ports(self) -> None:
        self.assertFalse(
            (PACKAGE_ROOT / "core" / "application" / "ports" / "capabilities").exists()
        )
        self.assertTrue(
            (PACKAGE_ROOT / "core" / "application" / "capabilities").is_dir()
        )
        self.assert_files_do_not_contain(
            PACKAGE_ROOT,
            ("foldmind_ai_core.core.application.ports.capabilities",),
        )

    def test_use_cases_and_workflows_depend_on_capabilities_not_agents(self) -> None:
        forbidden = ("foldmind_ai_core.core.application.agents",)
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "core" / "application" / "use_cases",
            forbidden,
        )
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "core" / "application" / "workflows",
            forbidden,
        )

    def test_application_services_do_not_hide_capability_protocols(self) -> None:
        services = PACKAGE_ROOT / "core" / "application" / "services"
        self.assertFalse((services / "retrieval_result_filter.py").exists())
        self.assert_files_do_not_contain(services, ("Protocol",))

    def test_inbound_ports_use_boundary_names(self) -> None:
        inbound_ports = PACKAGE_ROOT / "core" / "application" / "ports" / "inbound"
        for path in python_files(inbound_ports):
            self.assertFalse(path.name.endswith("_use_case.py"))
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("UseCasePort", text)

    def test_application_boundary_models_do_not_embed_domain_factories(self) -> None:
        for path in (
            PACKAGE_ROOT / "core" / "application" / "commands" / "projection.py",
            PACKAGE_ROOT / "core" / "application" / "projections" / "vector.py",
            PACKAGE_ROOT / "core" / "application" / "projections" / "graph.py",
            PACKAGE_ROOT / "core" / "application" / "results" / "retrieval.py",
        ):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("foldmind_ai_core.core.domain", text, f"{path} must stay pure")
            self.assertNotIn("@classmethod", text, f"{path} must use explicit mapper functions")

    def test_workflow_state_models_do_not_parse_llm_payloads(self) -> None:
        text = (
            PACKAGE_ROOT
            / "core"
            / "application"
            / "workflows"
            / "state"
            / "plan.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("from_mapping", text)
        self.assertNotIn("@classmethod", text)

    def test_recommendation_boundary_does_not_reuse_indexing_commands(self) -> None:
        for path in (
            PACKAGE_ROOT / "core" / "application" / "capabilities" / "retrieval.py",
            PACKAGE_ROOT
            / "core"
            / "application"
            / "use_cases"
            / "recommendation"
            / "recommend_folder.py",
        ):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("commands.indexing", text)
            self.assertNotIn("IndexDocumentCommand", text)

    def test_decoded_projection_events_stay_in_messaging_adapter(self) -> None:
        self.assertFalse(
            (PACKAGE_ROOT / "core" / "application" / "projections" / "events.py").exists()
        )
        self.assertTrue(
            (
                PACKAGE_ROOT
                / "adapters"
                / "inbound"
                / "messaging"
                / "projection_events.py"
            ).is_file()
        )

    def test_messaging_projection_consumers_use_plural_package(self) -> None:
        messaging = PACKAGE_ROOT / "adapters" / "inbound" / "messaging"

        self.assertFalse((messaging / "consumer").exists())
        self.assertTrue((messaging / "consumers").is_dir())
        self.assertFalse((messaging / "consumers" / "signal_vector_consumer.py").exists())
        self.assertTrue(
            (messaging / "consumers" / "document_signal_vector_consumer.py").is_file()
        )
        self.assert_files_do_not_contain(
            PACKAGE_ROOT,
            (
                "foldmind_ai_core.adapters.inbound.messaging.consumer.",
                "ProjectSignalVectorUseCase",
                "DeleteSignalVectorUseCase",
                "SignalVectorIndexedConsumer",
                "SignalVectorDeletedConsumer",
            ),
        )

    def test_http_application_error_mapping_has_boundary_name(self) -> None:
        http = PACKAGE_ROOT / "adapters" / "inbound" / "http"

        self.assertFalse((http / "error_responses.py").exists())
        self.assertTrue((http / "application_errors.py").is_file())

    def test_adapter_storage_models_do_not_import_application_or_domain_models(self) -> None:
        for path in (
            PACKAGE_ROOT / "adapters" / "outbound" / "postgres" / "models",
            PACKAGE_ROOT / "adapters" / "outbound" / "qdrant" / "models.py",
            PACKAGE_ROOT / "adapters" / "outbound" / "neo4j" / "models.py",
        ):
            if path.is_dir():
                files = python_files(path)
            else:
                files = [path]
            for file_path in files:
                text = file_path.read_text(encoding="utf-8")
                self.assertNotIn(
                    "foldmind_ai_core.core.application",
                    text,
                    f"{file_path} must stay adapter-persistence-only.",
                )
                self.assertNotIn(
                    "foldmind_ai_core.core.domain",
                    text,
                    f"{file_path} must stay adapter-persistence-only.",
                )
                self.assertNotIn(
                    "\ndef ",
                    text,
                    f"{file_path} must contain storage records only; put mapping in mappers.",
                )

    def test_application_model_modules_do_not_hide_mapper_functions(self) -> None:
        for path in python_files(PACKAGE_ROOT / "core" / "application" / "models"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "\ndef ",
                text,
                f"{path} must contain application models only; put mapping in factories.",
            )

    def test_application_result_package_does_not_hide_mapper_modules(self) -> None:
        for path in python_files(PACKAGE_ROOT / "core" / "application" / "results"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("mapper", path.stem)
            self.assertNotIn(
                "_mappers",
                path.stem,
                f"{path} must keep mapping functions in factories.",
            )
            self.assertNotIn(
                "foldmind_ai_core.core.domain",
                text,
                f"{path} must not expose domain models as use case results.",
            )

    def test_search_boundaries_return_application_results(self) -> None:
        find_signals = (
            PACKAGE_ROOT
            / "core"
            / "application"
            / "use_cases"
            / "retrieval"
            / "find_signals.py"
        ).read_text(encoding="utf-8")
        retrieval_capabilities = (
            PACKAGE_ROOT / "core" / "application" / "capabilities" / "retrieval.py"
        ).read_text(encoding="utf-8")
        find_folders = (
            PACKAGE_ROOT
            / "core"
            / "application"
            / "use_cases"
            / "recommendation"
            / "find_folders.py"
        ).read_text(encoding="utf-8")

        self.assertIn("SearchSignalsResult", find_signals)
        self.assertNotIn("SignalRetrievalResult", find_signals)
        self.assertIn("SearchFoldersResult", find_folders)
        self.assertNotIn("FolderRetrievalResult", find_folders)
        self.assertIn("SearchSignalsResult", retrieval_capabilities)
        self.assertIn("SearchFoldersResult", retrieval_capabilities)

    def test_application_command_package_does_not_expose_domain_models(self) -> None:
        for path in python_files(PACKAGE_ROOT / "core" / "application" / "commands"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "foldmind_ai_core.core.domain",
                text,
                f"{path} must not expose domain models as use case commands.",
            )

    def test_http_dto_models_do_not_contain_mapping_functions(self) -> None:
        for path in python_files(PACKAGE_ROOT / "adapters" / "inbound" / "http" / "dtos"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "\ndef ",
                text,
                f"{path} must contain transport models only; put conversion in mappers.",
            )
        self.assertTrue(
            (
                PACKAGE_ROOT
                / "adapters"
                / "inbound"
                / "http"
                / "mappers"
                / "transport_values.py"
            ).is_file()
        )

    def test_local_filenames_do_not_keep_ambiguous_role_names(self) -> None:
        forbidden_fragments = ("handler", "manager", "helper", "processor", "util")
        for root in (PACKAGE_ROOT, PROJECT_ROOT / "tests"):
            for path in root.rglob("*.py"):
                if "__pycache__" in path.parts:
                    continue
                filename = path.name.lower()
                for fragment in forbidden_fragments:
                    self.assertNotIn(
                        fragment,
                        filename,
                        f"{path} should use a concrete role name.",
                    )

    def test_documentation_does_not_reference_retired_names(self) -> None:
        for path in (PROJECT_ROOT / "README.md", PROJECT_ROOT / "README.ko.md"):
            text = path.read_text(encoding="utf-8")
            for token in (
                "AIQuery",
                "AnswerGeneratorAgent",
                "ChunkRelevanceValidatorAgent",
                "DeleteDocumentIndexRequest",
                "DeleteFolderIndexRequest",
                "DraftGeneratorAgent",
                "HostActionResultHandler",
                "IdeasExplorerAgent",
                "OutboxProjectionMessageHandler",
                "PromptRepository",
                "FilePromptRepository",
                "SummarizerAgent",
                "concepts JSON",
                "chunk_relevance_validation",
                "/indexing/documents/delete",
                "/indexing/folders/delete",
                "prompt_repository",
                "planning handler",
                "rag_context",
                "rag_generation",
                "relevance validation agent",
            ):
                self.assertNotIn(token, text, f"{path} references retired name {token}.")

    def test_application_internals_do_not_depend_on_inbound_ports(self) -> None:
        for path in python_files(PACKAGE_ROOT / "core" / "application"):
            if "ports" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "foldmind_ai_core.core.application.ports.inbound",
                text,
                f"{path} must not depend on inbound ports",
            )

    def test_indexing_application_does_not_leak_database_transaction_handles(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "core" / "application",
            (
                "conn: Any",
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
                "graph-ledger",
                "20260514_0001",
                "DocumentChunkingConfig()",
                "profile-v1",
                "document-profiling-v1",
                'source_version: str = "1"',
                'source_version: str = "1",',
                'or "1"',
            ),
        )

    def test_settings_do_not_keep_unprefixed_environment_aliases(self) -> None:
        settings = (PACKAGE_ROOT / "bootstrap" / "settings.py").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("AliasChoices", settings)
        for legacy_env_name in (
            '"POSTGRES_DSN"',
            '"QDRANT_URL"',
            '"NEO4J_USER"',
            '"AI_PROVIDER"',
            '"OPENAI_API_KEY"',
            '"OUTBOX_PROJECTION_TARGET"',
        ):
            self.assertNotIn(legacy_env_name, settings)

    def test_dead_graph_and_storage_layers_are_not_reintroduced(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT,
            (
                "concept_tenant_key",
                "concept_identity",
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
        text = (
            PACKAGE_ROOT
            / "core"
            / "domain"
            / "models"
            / "indexing"
            / "outbox.py"
        ).read_text(encoding="utf-8")
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

    def test_qdrant_stores_do_not_expose_capability_flags(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "adapters" / "outbound" / "qdrant",
            ("supports_keyword_search", "supports_document_search", "supports_"),
        )

    def test_outbound_adapters_do_not_depend_on_application_services(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "adapters" / "outbound",
            ("foldmind_ai_core.core.application.services",),
        )

    def test_application_orchestrators_depend_on_ports_not_concrete_use_cases(self) -> None:
        forbidden = ("foldmind_ai_core.core.application.use_cases",)
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "core" / "application" / "workflows",
            forbidden,
        )
        for path in python_files(PACKAGE_ROOT / "core" / "application" / "use_cases"):
            if path.name == "__init__.py":
                continue
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"{path} must depend on a port instead")

    def test_application_workflows_do_not_contain_runtime_adapter_state(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "core" / "application" / "workflows",
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
                "foldmind_ai_core.core.application.ports.inbound",
                "foldmind_ai_core.core.application.use_cases",
                "foldmind_ai_core.adapters.inbound",
                "foldmind_ai_core.bootstrap",
                "fastapi",
            ),
        )

    def test_workflow_artifact_registry_hides_generic_artifact_access(self) -> None:
        self.assertFalse(
            (
                PACKAGE_ROOT
                / "core"
                / "application"
                / "workflows"
                / "artifacts"
                / "store.py"
            ).exists()
        )
        from foldmind_ai_core.core.application.workflows.artifacts.registry import (
            WorkflowArtifactRegistry,
        )

        public_methods = {
            name for name in dir(WorkflowArtifactRegistry)
            if not name.startswith("_")
        }

        self.assertIn("record_step_outcome", public_methods)
        self.assertFalse(
            {"get", "get_list", "set", "append_output"} & public_methods,
            "Workflow artifact access should be exposed through typed methods.",
        )

    def test_workflow_action_specs_and_functions_cover_all_action_types(self) -> None:
        from foldmind_ai_core.core.application.workflows.state.plan import WorkflowActionType
        from foldmind_ai_core.core.application.workflows.steps.executor import WorkflowStepExecutor
        from foldmind_ai_core.core.application.workflows.steps.specs import STEP_SPECS

        dependency = cast(Any, object())
        executor = WorkflowStepExecutor(
            find_documents=dependency,
            find_signals=dependency,
            find_folders=dependency,
            recommend_folder=dependency,
            folder_recommendation_sources=dependency,
            context_generator=dependency,
            host_action_builder=dependency,
            artifacts=dependency,
            host_action_results=dependency,
        )

        action_types = set(WorkflowActionType)
        self.assertEqual(action_types, set(STEP_SPECS))
        self.assertEqual(action_types, set(executor._step_functions))

    def test_inbound_http_and_app_factory_depend_on_inbound_ports(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "adapters" / "inbound" / "http",
            (
                "foldmind_ai_core.core.application.use_cases",
                "foldmind_ai_core.core.application.agents",
                "foldmind_ai_core.core.application.workflows",
                "foldmind_ai_core.core.application.ports.outbound",
                "foldmind_ai_core.adapters.outbound",
                "foldmind_ai_core.infrastructure",
                "foldmind_ai_core.bootstrap",
                "langgraph",
            ),
        )
        app_factory = PACKAGE_ROOT / "bootstrap" / "app_factory.py"
        self.assertNotIn(
            "foldmind_ai_core.core.application.use_cases",
            app_factory.read_text(encoding="utf-8"),
        )

    def test_use_case_container_does_not_build_http_app(self) -> None:
        text = (
            PACKAGE_ROOT
            / "bootstrap"
            / "container"
            / "use_cases.py"
        ).read_text(encoding="utf-8")
        for token in (
            "from fastapi",
            "create_app",
            "def build_app",
            "def build_configured_app",
        ):
            self.assertNotIn(token, text)

    def test_use_case_container_does_not_build_workflow_runtime_adapter(self) -> None:
        text = (
            PACKAGE_ROOT
            / "bootstrap"
            / "container"
            / "use_cases.py"
        ).read_text(encoding="utf-8")
        for token in (
            "adapters.outbound.workflow_runtime",
            "LangGraphWorkflowGraph",
            "build_workflow_checkpointer",
        ):
            self.assertNotIn(token, text)

    def test_api_use_case_bundle_is_not_defined_in_http_factory(self) -> None:
        app_factory = (
            PACKAGE_ROOT
            / "bootstrap"
            / "app_factory.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("@dataclass", app_factory)
        self.assertTrue((PACKAGE_ROOT / "bootstrap" / "api_use_cases.py").is_file())

    def test_bootstrap_storage_bundle_does_not_use_repository_as_catch_all(self) -> None:
        container = PACKAGE_ROOT / "bootstrap" / "container"

        self.assertFalse((container / "repositories.py").exists())
        self.assertTrue((container / "storage.py").is_file())
        self.assert_files_do_not_contain(
            container,
            (
                "ApplicationRepositories",
                "OutboxProjectionRepositories",
                "ProjectionRepositories",
                "build_application_repositories",
                "build_outbox_projection_repositories",
                "bootstrap.container.repositories",
            ),
        )

    def test_http_routers_do_not_duplicate_application_error_mapping(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "adapters" / "inbound" / "http" / "routers",
            (
                "InvalidInputError",
                "ResourceNotFoundError",
                "NoCandidatesError",
                "HTTPException",
            ),
        )

    def test_http_mappers_do_not_keep_domain_output_model_mappers(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "adapters" / "inbound" / "http" / "mappers",
            (
                "_from_model",
                "foldmind_ai_core.core.domain",
                "host_action_result_from_dto",
            ),
        )

    def test_retrieval_http_mapper_does_not_own_workflow_outputs(self) -> None:
        http_mappers = PACKAGE_ROOT / "adapters" / "inbound" / "http" / "mappers"
        retrieval_mapper = (http_mappers / "retrieval.py").read_text(encoding="utf-8")

        self.assertTrue((http_mappers / "workflow_outputs.py").is_file())
        self.assertNotIn(
            "foldmind_ai_core.core.application.results.workflow",
            retrieval_mapper,
        )
        self.assertNotIn("TaskOutputResult", retrieval_mapper)

    def test_retrieval_http_dtos_do_not_own_workflow_outputs(self) -> None:
        http_dtos = PACKAGE_ROOT / "adapters" / "inbound" / "http" / "dtos"
        retrieval_dtos = (http_dtos / "retrieval.py").read_text(encoding="utf-8")

        self.assertTrue((http_dtos / "workflow_outputs.py").is_file())
        for workflow_output_name in (
            "AssistantClarificationDTO",
            "DocumentRecommendationResultDTO",
            "DocumentSearchResultDTO",
            "DraftResultDTO",
            "FolderRecommendationResultDTO",
            "RelatedRecommendationResultDTO",
        ):
            self.assertNotIn(workflow_output_name, retrieval_dtos)

    def test_retrieval_steps_do_not_own_artifact_assembly(self) -> None:
        steps = PACKAGE_ROOT / "core" / "application" / "workflows" / "steps"
        retrieval_steps = (steps / "retrieval.py").read_text(encoding="utf-8")

        self.assertTrue((steps / "retrieval_artifacts.py").is_file())
        for artifact_function in (
            "def signal_evidence_chunk",
            "def signal_text_chunk",
            "def retrieved_document_from_result",
            "def related_retrieval",
        ):
            self.assertNotIn(artifact_function, retrieval_steps)

    def test_workflow_host_action_builder_does_not_depend_on_step_options(self) -> None:
        builder = (
            PACKAGE_ROOT
            / "core"
            / "application"
            / "workflows"
            / "host_actions"
            / "builder.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("workflows.steps.options", builder)
        self.assertTrue(
            (
                PACKAGE_ROOT
                / "core"
                / "application"
                / "workflows"
                / "option_values.py"
            ).is_file()
        )

    def test_context_generation_does_not_keep_loose_rag_wrapper_modules(self) -> None:
        application = PACKAGE_ROOT / "core" / "application"

        self.assertFalse((application / "agents" / "rag_generation.py").exists())
        self.assertFalse((application / "services" / "rag_context.py").exists())
        self.assertTrue((application / "services" / "retrieved_context.py").is_file())

    def test_application_factories_use_directional_conversion_names(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "core" / "application" / "factories",
            ("retrieval_result_from_result",),
        )

    def test_outbound_domain_codec_has_explicit_name(self) -> None:
        self.assertFalse((PACKAGE_ROOT / "adapters" / "outbound" / "model_codec.py").exists())
        self.assertTrue(
            (PACKAGE_ROOT / "adapters" / "outbound" / "domain_model_codec.py").is_file()
        )
        self.assertFalse(
            (
                PACKAGE_ROOT
                / "adapters"
                / "outbound"
                / "postgres"
                / "profile_repository.py"
            ).exists()
        )
        self.assertTrue(
            (
                PACKAGE_ROOT
                / "adapters"
                / "outbound"
                / "postgres"
                / "index_repository.py"
            ).is_file()
        )
        self.assertFalse(
            (
                PACKAGE_ROOT
                / "adapters"
                / "outbound"
                / "postgres"
                / "models"
                / "profile.py"
            ).exists()
        )
        self.assertFalse(
            (
                PACKAGE_ROOT
                / "adapters"
                / "outbound"
                / "postgres"
                / "mappers"
                / "profile.py"
            ).exists()
        )
        self.assertTrue(
            (
                PACKAGE_ROOT
                / "adapters"
                / "outbound"
                / "postgres"
                / "models"
                / "document_signal.py"
            ).is_file()
        )
        self.assertTrue(
            (
                PACKAGE_ROOT
                / "adapters"
                / "outbound"
                / "postgres"
                / "mappers"
                / "document_signal.py"
            ).is_file()
        )
        self.assertFalse(
            (
                PROJECT_ROOT
                / "migrations"
                / "versions"
                / "20260513_0001_create_profile_storage.py"
            ).exists()
        )
        self.assertTrue(
            (
                PROJECT_ROOT
                / "migrations"
                / "versions"
                / "20260513_0001_create_projection_storage.py"
            ).is_file()
        )
        self.assert_files_do_not_contain(
            PACKAGE_ROOT,
            (
                "adapters.outbound.model_codec",
                "adapters.outbound.postgres.profile_repository",
                "adapters.outbound.postgres.models.profile",
                "adapters.outbound.postgres.mappers.profile",
                "PostgresProfileRepository",
                "model_value",
                "restore_model_value",
            ),
        )

    def test_inbound_messaging_depends_on_ports_and_domain_not_application_internals(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "adapters" / "inbound" / "messaging",
            (
                "handle_outbox_event",
                "foldmind_ai_core.core.application.services",
                "foldmind_ai_core.core.application.use_cases",
                "foldmind_ai_core.core.application.agents",
                "foldmind_ai_core.core.application.workflows",
                "foldmind_ai_core.core.application.ports.outbound",
                "foldmind_ai_core.adapters.outbound",
                "foldmind_ai_core.bootstrap",
                "foldmind_ai_core.workers",
                "OutboxProjectionMessageConsumer",
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
                "foldmind_ai_core.core.application.ports.inbound",
                "foldmind_ai_core.core.application.use_cases",
                "foldmind_ai_core.adapters.inbound",
                "foldmind_ai_core.bootstrap",
                "fastapi",
            ),
        )

    def test_old_ai_core_package_is_removed(self) -> None:
        self.assertFalse((PROJECT_ROOT / "src" / "ai_core").exists())
        self.assert_files_do_not_contain(
            PACKAGE_ROOT,
            ("import ai_core", "from ai_core", "__ai_core_checkpoint_type__"),
        )

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

    def test_dead_letter_producer_uses_explicit_name(self) -> None:
        kafka = PACKAGE_ROOT / "adapters" / "outbound" / "kafka"
        self.assertFalse((kafka / "dlq_producer.py").exists())
        self.assertTrue((kafka / "dead_letter_producer.py").is_file())
        self.assertFalse((PROJECT_ROOT / "scripts" / "replay_dlq.py").exists())
        self.assertTrue(
            (PROJECT_ROOT / "scripts" / "replay_dead_letter_events.py").is_file()
        )
        settings = (PACKAGE_ROOT / "bootstrap" / "settings.py").read_text(encoding="utf-8")
        self.assertNotIn("kafka_dlq_topic", settings)
        self.assertNotIn("KAFKA_DLQ_TOPIC", settings)
        self.assert_files_do_not_contain(
            PACKAGE_ROOT,
            (
                "KafkaDlqProducer",
                "DlqProducer",
                "dlq_producer",
            ),
        )

    def test_neo4j_graph_store_does_not_keep_local_session_provider(self) -> None:
        text = (
            PACKAGE_ROOT
            / "adapters"
            / "outbound"
            / "neo4j"
            / "stores"
            / "graph_store.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("Neo4jSessionProvider", text)
        self.assertNotIn("Protocol", text)

    def test_test_tree_does_not_keep_empty_future_scaffolds(self) -> None:
        tests_root = PROJECT_ROOT / "tests"
        for package_path in (
            tests_root / "e2e",
            tests_root / "integration",
            tests_root / "contract" / "workflow_api",
            tests_root / "unit" / "services",
            tests_root / "unit" / "workflows",
        ):
            self.assertFalse(package_path.exists())

        integration = tests_root / "integration"
        for package_name in (
            "graph_store",
            "ontology_reasoner",
            "vector_store",
            "workflow_store",
        ):
            package_path = integration / package_name
            self.assertFalse((package_path / "__init__.py").exists())
            self.assertFalse(list(package_path.glob("*.py")))

    def test_prompts_do_not_keep_duplicate_root_source_copies(self) -> None:
        from foldmind_ai_core.core.application.services.prompts import (
            PROMPT_ANSWER_GENERATION,
            PROMPT_CHUNK_RELEVANCE_FILTERING,
            PROMPT_DOCUMENT_PROFILING,
            PROMPT_DRAFT_GENERATION,
            PROMPT_IDEAS_EXPLORATION,
            PROMPT_SUMMARIZATION,
            PROMPT_WORKFLOW_PLANNING,
        )

        self.assertFalse((PROJECT_ROOT / "resources" / "prompts").exists())
        prompt_names = {
            path.stem for path in (PACKAGE_ROOT / "resources" / "prompts").glob("*.md")
        }
        self.assertEqual(
            prompt_names,
            {
                PROMPT_ANSWER_GENERATION,
                PROMPT_CHUNK_RELEVANCE_FILTERING,
                PROMPT_DOCUMENT_PROFILING,
                PROMPT_DRAFT_GENERATION,
                PROMPT_IDEAS_EXPLORATION,
                PROMPT_SUMMARIZATION,
                PROMPT_WORKFLOW_PLANNING,
            },
        )

    def test_environment_examples_live_under_examples_env(self) -> None:
        self.assertFalse((PROJECT_ROOT / ".env.example").exists())
        self.assertEqual(
            {
                path.name for path in (PROJECT_ROOT / "examples" / "env").glob("*.env")
            },
            {"external.env", "local-postgres-external-services.env", "local.env"},
        )
