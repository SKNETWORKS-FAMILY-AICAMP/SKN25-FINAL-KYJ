from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.ports.inbound.indexing import (
    DocumentIndexingServicePort,
    FolderIndexingServicePort,
)
from foldmind_ai_core.core.application.ports.inbound.workflow import TaskWorkflowServicePort


@dataclass(slots=True)
class APIApplicationServices:
    document_indexing: DocumentIndexingServicePort
    folder_indexing: FolderIndexingServicePort
    task_workflow: TaskWorkflowServicePort
