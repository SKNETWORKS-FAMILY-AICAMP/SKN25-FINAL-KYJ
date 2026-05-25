from __future__ import annotations

import ast
import unittest
from pathlib import Path

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "src").exists()
)
PACKAGE_ROOT = PROJECT_ROOT / "src" / "foldmind_ai_core"


def python_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
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
                self.assertNotIn(token, text, f"{path} must not contain {token}")

    def public_class_names(self, path: Path) -> list[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return [
            node.name
            for node in tree.body
            if isinstance(node, ast.ClassDef) and not node.name.startswith("_")
        ]

    def public_function_names(self, path: Path) -> list[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return [
            node.name
            for node in tree.body
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
            and not node.name.startswith("_")
        ]

    def test_core_owns_application_and_domain_packages(self) -> None:
        self.assertTrue((PACKAGE_ROOT / "core" / "application").is_dir())
        self.assertTrue((PACKAGE_ROOT / "core" / "domain").is_dir())
        self.assertFalse((PACKAGE_ROOT / "application").exists())
        self.assertFalse((PACKAGE_ROOT / "domain").exists())

    def test_python_package_directories_have_empty_init_files(self) -> None:
        resources = PACKAGE_ROOT / "resources"
        source_package_directories = {
            path
            for path in PACKAGE_ROOT.rglob("*")
            if path.is_dir()
            and "__pycache__" not in path.parts
            and path != resources
            and resources not in path.parents
        } | {PACKAGE_ROOT}
        test_package_directories = {
            path.parent
            for path in (PROJECT_ROOT / "tests").rglob("*.py")
            if "__pycache__" not in path.parts
        }

        for directory in sorted(source_package_directories | test_package_directories):
            init_file = directory / "__init__.py"
            self.assertTrue(init_file.is_file(), f"{directory} needs __init__.py")
            self.assertEqual(
                "",
                init_file.read_text(encoding="utf-8").strip(),
                f"{init_file} must stay empty.",
            )

        for root in (resources, PROJECT_ROOT / "migrations", PROJECT_ROOT / "scripts"):
            self.assertEqual(
                [],
                sorted(root.rglob("__init__.py")),
                f"{root} is data or standalone code, not a Python package.",
            )

    def test_domain_does_not_depend_on_application_or_adapters(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "core" / "domain",
            (
                "foldmind_ai_core.core.application",
                "foldmind_ai_core.adapters",
                "foldmind_ai_core.bootstrap",
                "fastapi",
                "langgraph",
                "qdrant_client",
                "psycopg",
                "from neo4j",
            ),
        )

    def test_application_does_not_depend_on_adapters_or_frameworks(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "core" / "application",
            (
                "foldmind_ai_core.adapters",
                "foldmind_ai_core.bootstrap",
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
                "foldmind_ai_core.core.application.services",
                "foldmind_ai_core.core.application.agents",
                "foldmind_ai_core.adapters",
                "foldmind_ai_core.bootstrap",
                "fastapi",
                "langgraph",
                "raise NotImplementedError",
            ),
        )

    def test_application_entrypoints_are_application_services(self) -> None:
        application = PACKAGE_ROOT / "core" / "application"
        self.assertFalse((application / "use_cases").exists())
        self.assertTrue((application / "ports" / "inbound").is_dir())
        self.assertTrue((application / "services").is_dir())
        self.assert_files_do_not_contain(
            PACKAGE_ROOT,
            (
                "UseCase",
                "use_cases",
                "TracedUseCase",
                "APIUseCases",
            ),
        )

    def test_application_services_root_does_not_hide_service_files(self) -> None:
        service_root = PACKAGE_ROOT / "core" / "application" / "services"
        root_python_files = sorted(path.name for path in service_root.glob("*.py"))
        self.assertEqual(["__init__.py"], root_python_files)

        for package_name in (
            "indexing",
            "projection",
            "recommendation",
            "retrieval",
            "workflow",
        ):
            self.assertTrue((service_root / package_name / "__init__.py").is_file())

        retired_service_files = {
            "outbox_events.py",
            "prompts.py",
            "blocking_io.py",
            "retrieved_context.py",
            "embedding_results.py",
            "vector_projection_spec.py",
        }
        self.assertFalse(
            retired_service_files
            & {path.name for path in service_root.rglob("*.py")}
        )

    def test_application_service_files_match_application_responsibilities(self) -> None:
        service_root = PACKAGE_ROOT / "core" / "application" / "services"
        expected_files = {
            "indexing": {
                "__init__.py",
                "document_indexing_service.py",
                "folder_indexing_service.py",
                "folder_signal_invalidation_service.py",
            },
            "projection": {
                "__init__.py",
                "document_vector_projection_service.py",
                "freshness.py",
                "folder_vector_projection_service.py",
                "graph_projection_service.py",
            },
            "recommendation": {
                "__init__.py",
                "folder_recommendation_service.py",
                "folder_recommendation_source_resolver.py",
            },
            "retrieval": {
                "__init__.py",
                "document_retrieval_service.py",
                "document_search_service.py",
                "folder_retrieval_service.py",
                "folder_search_service.py",
                "policy.py",
                "ranking.py",
                "scope_resolver.py",
                "signal_retrieval_service.py",
                "signal_search_service.py",
            },
            "workflow": {"__init__.py", "task_workflow_service.py"},
        }
        for package_name, filenames in expected_files.items():
            self.assertEqual(
                filenames,
                {path.name for path in (service_root / package_name).glob("*.py")},
            )

    def test_domain_models_hold_core_concepts_only(self) -> None:
        domain_models = PACKAGE_ROOT / "core" / "domain" / "models"
        self.assertEqual(
            [],
            [
                path
                for path in domain_models.iterdir()
                if path.is_dir() and path.name != "__pycache__"
            ],
        )
        self.assertFalse((domain_models / "generation").exists())
        self.assertFalse((domain_models / "retrieval").exists())
        self.assertFalse((domain_models / "profiling.py").exists())
        self.assertFalse((domain_models / "indexing" / "outbox.py").exists())
        self.assertFalse((domain_models / "document_index_records.py").exists())
        self.assertFalse((domain_models / "folder_index_records.py").exists())
        self.assertFalse((domain_models / "document_search.py").exists())
        self.assertFalse((domain_models / "search.py").exists())

        for path in python_files(domain_models):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("TaskSnapshotRevision", text, str(path))
            self.assertNotIn("Document" + "ChunkingConfig", text, str(path))
            self.assertNotIn("Document" + "IndexDigestPayload", text, str(path))
            self.assertNotIn("Document" + "IndexInput", text, str(path))
            self.assertNotIn("Document" + "SignalInputDigest", text, str(path))
            self.assertNotIn("Document" + "ChunkRecord", text, str(path))
            self.assertNotIn("Task" + "CreationInput", text, str(path))
            self.assertNotIn("Task" + "AppendInput", text, str(path))
            self.assertNotIn("core.application." + "results", text, str(path))

        expected_domain_classes = {
            "document_sources.py": {
                "DocumentSourceIdentity",
                "DocumentSourceState",
                "SourceDocument",
            },
            "folder_sources.py": {"FolderSourceIdentity", "SourceFolder"},
            "document_folder_relations.py": {"SourceDocumentFolderRelationSnapshot"},
            "document_chunks.py": {
                "DocumentChunkingPolicy",
                "DocumentIndexingPolicy",
                "DocumentChunk",
            },
            "document_index_state.py": {
                "DocumentIndexState",
            },
            "folder_index_state.py": {
                "FolderIndexState",
                "FolderSignalRefreshStatus",
            },
            "document_signals.py": {
                "DocumentSignalType",
                "DocumentSignalEvidence",
                "DocumentSignal",
            },
            "folder_signals.py": {"FolderSignalType", "FolderSignal"},
            "tasks.py": {
                "TaskStatus",
                "TaskEventType",
                "TaskInputStatus",
                "TaskJobStatus",
                "TaskOutputType",
                "TaskContext",
                "TaskInputEntry",
                "TaskEvent",
                "TaskJobResult",
                "TaskJob",
                "TaskFinalResult",
                "TaskAnalysis",
                "TaskSnapshot",
            },
            "outbox.py": {
                "OutboxSourceKind",
                "OutboxEventType",
                "OutboxEvent",
            },
            "vector_projection_state.py": {"VectorProjectionState"},
            "host_actions.py": {
                "HostActionType",
                "HostActionStatus",
                "HostActionResultType",
                "HostActionPolicy",
                "CreateFolderInput",
                "CreateDocumentInput",
                "UpdateDocumentInput",
                "MoveDocumentInput",
                "LinkDocumentsInput",
                "CreateFolderOutput",
                "CreateDocumentOutput",
                "UpdateDocumentOutput",
                "MoveDocumentOutput",
                "LinkDocumentsOutput",
                "HostAction",
                "HostActionResult",
                "ActionPlan",
            },
        }
        for relative_path, classes in expected_domain_classes.items():
            self.assertEqual(classes, set(self.public_class_names(domain_models / relative_path)))

    def test_domain_models_do_not_hold_application_commands_or_results(self) -> None:
        allowed_domain_result_classes = {
            "HostActionResult",
            "HostActionResultType",
            "TaskFinalResult",
            "TaskJobResult",
        }
        for path in python_files(PACKAGE_ROOT / "core" / "domain" / "models"):
            for class_name in self.public_class_names(path):
                self.assertFalse(
                    class_name.endswith(("Command", "Query")),
                    f"{class_name} in {path} is an application entrypoint model.",
                )
                if class_name.endswith("Result"):
                    self.assertIn(
                        class_name,
                        allowed_domain_result_classes,
                        f"{class_name} in {path} should live in application results.",
                    )

    def test_application_models_hold_commands_results_and_port_payloads(self) -> None:
        application = PACKAGE_ROOT / "core" / "application"
        for retired_package in (
            "commands",
            "results",
            "queries",
            "factories",
            "projections",
        ):
            self.assertFalse((application / retired_package).exists())
        expected_model_files = {
            "__init__.py",
            "generation.py",
            "indexing.py",
            "llm.py",
            "projection_commands.py",
            "recommendation.py",
            "retrieval.py",
            "search.py",
            "task_commands.py",
            "task_results.py",
            "vector_projection.py",
        }
        self.assertEqual(
            expected_model_files,
            {path.name for path in (application / "models").glob("*.py")},
        )
        self.assertTrue((application / "mappers").is_dir())
        self.assertFalse((application / "models" / "projection.py").exists())
        self.assertFalse((application / "models" / "graph_projection.py").exists())
        self.assertFalse((application / "models" / "projection_sources.py").exists())
        self.assertFalse((application / "models" / "workflow.py").exists())
        self.assertFalse((application / "models" / "task_state.py").exists())
        self.assertFalse((application / "models" / "task_outputs.py").exists())
        self.assertFalse((application / "models" / "outbox.py").exists())
        self.assertFalse((application / "models" / "retrieval_matches.py").exists())
        self.assertFalse(
            (application / "models" / ("projection_" + "inputs.py")).exists()
        )
        for path in python_files(application / "models"):
            self.assertEqual([], self.public_function_names(path), str(path))

        application_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in python_files(application)
            if "__pycache__" not in path.parts
        )
        for token in (
            "class CreateTaskCommand",
            "class ProjectDocumentCommand",
            "class FolderRecommendationSource",
            "class RecordActionResult",
            "class GeneratedTextResult",
            "class DocumentRetrievalResult",
        ):
            self.assertIn(token, application_text)
        for token in (
            "TaskSnapshotRevision",
            "Deleted" + "DocumentIdentity",
            "Deleted" + "FolderIdentity",
            "Document" + "IndexChange",
            "Folder" + "IndexChange",
            "Folder" + "RelationChange",
            "TaskFinal" + "ResultResult",
            "TaskJob" + "ItemResult",
            "TaskJob" + "ResultItemResult",
            "class Task" + "Result",
        ):
            self.assertNotIn(token, application_text)

        self.assertFalse((application / "models" / "keyword_search.py").exists())
        retrieval_results = (
            application / "models" / "retrieval.py"
        ).read_text(encoding="utf-8")
        self.assertIn("DocumentTitleKeywordMatch", retrieval_results)
        self.assertNotIn("DocumentChunkKeywordMatch", retrieval_results)

    def test_application_results_do_not_live_in_domain_models(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "core" / "domain" / "models",
            (
                "GeneratedTextResult",
                "DraftResult",
                "RetrievalResult",
                "DocumentRetrievalResult",
                "Search" + "DocumentsResult",
                "Search" + "SignalsResult",
                "Search" + "FoldersResult",
                "Recommend" + "FolderResult",
            ),
        )

    def test_domain_services_are_service_objects_not_function_modules(self) -> None:
        domain_services = PACKAGE_ROOT / "core" / "domain" / "services"
        expected_classes = {
            "__init__.py": [],
            "confidence_service.py": ["ConfidenceService"],
            "document_chunker.py": ["DocumentChunker"],
            "document_indexing_invariant_service.py": [
                "DocumentIndexingInvariantService"
            ],
            "document_signal_service.py": ["DocumentSignalService"],
            "folder_projection_digest_service.py": ["FolderProjectionDigestService"],
            "folder_signal_service.py": ["FolderSignalService"],
            "workflow_domain_service.py": ["WorkflowDomainService"],
            "workflow_input_service.py": ["WorkflowInputService"],
        }
        for path in sorted(domain_services.glob("*.py")):
            self.assertEqual([], self.public_function_names(path), str(path))
            self.assertEqual(expected_classes[path.name], self.public_class_names(path))

    def test_postgres_repositories_do_not_own_sessions_or_rows_at_boundary(self) -> None:
        repository_root = PACKAGE_ROOT / "adapters" / "outbound" / "postgres" / "repository"
        for path in python_files(repository_root):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("AsyncSession", text, str(path))
            self.assertNotIn("list[Any]", text, str(path))

    def test_repository_ports_expose_domain_models_only(self) -> None:
        for root in (
            PACKAGE_ROOT / "core" / "application" / "ports" / "outbound" / "repository",
            PACKAGE_ROOT / "adapters" / "outbound" / "postgres" / "repository",
        ):
            self.assert_files_do_not_contain(
                root,
                (
                    "foldmind_ai_core.core.application.models",
                    "foldmind_ai_core.core.application." + "results",
                    "foldmind_ai_core.core.application." + "queries",
                    "foldmind_ai_core.core.application.models.projection import",
                    "foldmind_ai_core.core.application.models.workflow",
                ),
            )

    def test_postgres_store_package_keeps_table_oriented_names(self) -> None:
        store_root = PACKAGE_ROOT / "adapters" / "outbound" / "postgres" / "store"
        self.assertFalse((store_root / "document_search_store.py").exists())
        self.assertFalse((store_root / "folder_signal_input_store.py").exists())
        self.assertFalse((PACKAGE_ROOT / "adapters" / "outbound" / "postgres" / "queries").exists())
        self.assertFalse((PACKAGE_ROOT / "adapters" / "outbound" / "postgres" / "search").exists())
        self.assertFalse(
            (
                PACKAGE_ROOT
                / "adapters"
                / "outbound"
                / "postgres"
                / ("document_" + "read_session.py")
            ).exists()
        )
        self.assertFalse(
            (PACKAGE_ROOT / "core" / "application" / "ports" / "outbound" / "search").exists()
        )
        self.assertFalse(
            (
                PACKAGE_ROOT
                / "core"
                / "application"
                / "ports"
                / "outbound"
                / "session"
                / ("document_" + "read_session.py")
            ).exists()
        )

    def test_outbound_adapters_do_not_depend_on_application_services(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT / "adapters" / "outbound",
            ("foldmind_ai_core.core.application.services",),
        )

    def test_retired_legacy_names_are_not_used(self) -> None:
        self.assert_files_do_not_contain(
            PACKAGE_ROOT,
            (
                "Document" + "ProfilerAgent",
                "document_" + "profiling",
                "document_" + "profile_prompt",
                "FOLDMIND_" + "DOCUMENT_PROFILE",
                "FolderSignal" + "RefreshCommit",
                "FolderSignal" + "Extraction",
                "foldmind_ai_core.core.domain.models." + "generation",
                "foldmind_ai_core.core.domain.models." + "retrieval",
                "foldmind_ai_core.core.domain.models.indexing." + "outbox",
                "Document" + "KeywordSearch",
                "document_" + "keyword_search",
                "postgres." + "search",
                "document_" + "read_session",
                "Document" + "ReadSession",
            ),
        )
        self.assert_files_do_not_contain(
            PROJECT_ROOT / "tests",
            (
                "Document" + "ProfilerAgent",
                "document_" + "profiling",
                "FolderSignal" + "RefreshCommit",
                "FolderSignal" + "Extraction",
                "foldmind_ai_core.core.domain.models." + "generation",
                "foldmind_ai_core.core.domain.models." + "retrieval",
                "foldmind_ai_core.core.domain.models.indexing." + "outbox",
            ),
        )
