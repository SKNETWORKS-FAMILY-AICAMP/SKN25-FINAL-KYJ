from __future__ import annotations

import unittest

from ai_core.common import Metadata, Vector
from ai_core.domain import TaskSnapshot as DomainTaskSnapshot
from ai_core.schemas import (
    HostAction,
    HostActionType,
    MoveDocumentInput,
    RequestContext,
    SearchScope,
    TaskAnalysis,
    TaskEvent,
    TaskRequest,
    TaskSnapshot,
    TaskStatus,
)
from ai_core.application.ports import TaskStore


class InMemoryTaskStore:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], TaskSnapshot] = {}

    def create(self, request: TaskRequest, snapshot: TaskSnapshot) -> None:
        self.items[(request.tenant, request.task_id)] = snapshot

    def get(self, *, tenant: str, task_id: str) -> TaskSnapshot | None:
        return self.items.get((tenant, task_id))

    def save(self, snapshot: TaskSnapshot) -> None:
        self.items[(snapshot.tenant, snapshot.task_id)] = snapshot

    def append_event(self, *, tenant: str, task_id: str, event: TaskEvent) -> None:
        snapshot = self.items[(tenant, task_id)]
        snapshot.events.append(event)


class ContractTests(unittest.TestCase):
    def test_common_types_are_importable(self) -> None:
        metadata: Metadata = {"source": "unit-test"}
        vector: Vector = [0.1, 0.2, 0.3]

        self.assertEqual(metadata["source"], "unit-test")
        self.assertEqual(len(vector), 3)

    def test_host_action_accepts_typed_payload(self) -> None:
        action = HostAction(
            action_type=HostActionType.MOVE_DOCUMENT,
            summary="Move the document to the recommended folder.",
            input=MoveDocumentInput(
                entity_type="document",
                entity_id="doc-1",
                target_folder_id="folder-1",
            ),
        )

        self.assertEqual(action.action_type, HostActionType.MOVE_DOCUMENT)
        self.assertIsInstance(action.input, MoveDocumentInput)

    def test_query_context_and_scope_model_app_server_boundary(self) -> None:
        context = RequestContext(tenant="tenant-1", user_id="user-1")
        scope = SearchScope(entity_type="document", folder_ids=("folder-1",))

        self.assertEqual(context.tenant, "tenant-1")
        self.assertEqual(scope.folder_ids, ("folder-1",))

    def test_task_snapshot_keeps_workflow_context(self) -> None:
        request = TaskRequest(
            task_id="task-1",
            tenant="tenant-1",
            request="Summarize related meeting notes.",
            user_id="user-1",
        )
        snapshot = TaskSnapshot(
            task_id=request.task_id,
            tenant=request.tenant,
            request=request.request,
            status=TaskStatus.COMPLETED,
            analysis=TaskAnalysis(response="Done."),
            user_id=request.user_id,
        )

        self.assertEqual(snapshot.user_id, "user-1")
        self.assertEqual(snapshot.status, TaskStatus.COMPLETED)

    def test_schemas_reexport_domain_models(self) -> None:
        self.assertIs(TaskSnapshot, DomainTaskSnapshot)

    def test_application_ports_are_structural(self) -> None:
        store: TaskStore = InMemoryTaskStore()
        request = TaskRequest(task_id="task-1", tenant="tenant-1", request="Test")
        snapshot = TaskSnapshot(
            task_id=request.task_id,
            tenant=request.tenant,
            request=request.request,
            status=TaskStatus.COMPLETED,
            analysis=TaskAnalysis(response="Done."),
        )

        store.create(request, snapshot)

        self.assertIs(store.get(tenant="tenant-1", task_id="task-1"), snapshot)


if __name__ == "__main__":
    unittest.main()
