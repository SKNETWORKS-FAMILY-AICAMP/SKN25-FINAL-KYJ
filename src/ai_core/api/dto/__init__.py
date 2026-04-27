"""API DTOs."""

from ai_core.api.dto.actions import RecordHostActionResultRequest
from ai_core.api.dto.indexing import (
    DeleteDocumentIndexRequest,
    IndexDocumentRequest,
    IndexDocumentResponse,
)
from ai_core.api.dto.tasks import CreateTaskRequest, TaskSnapshotResponse

__all__ = [
    "CreateTaskRequest",
    "DeleteDocumentIndexRequest",
    "IndexDocumentRequest",
    "IndexDocumentResponse",
    "RecordHostActionResultRequest",
    "TaskSnapshotResponse",
]
