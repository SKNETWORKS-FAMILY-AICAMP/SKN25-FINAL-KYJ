from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.ports.inbound.indexing import (
    DeleteDocumentIndexInboundPort,
    DeleteFolderIndexInboundPort,
    IndexDocumentInboundPort,
    IndexFolderInboundPort,
    UpdateDocumentFolderRelationsInboundPort,
)
from foldmind_ai_core.core.application.ports.inbound.workflow import (
    GetTaskInboundPort,
    RecordActionResultInboundPort,
    RemoveTaskInputInboundPort,
    RunTaskInboundPort,
)


@dataclass(slots=True)
class APIUseCases:
    index_document: IndexDocumentInboundPort
    delete_document_index: DeleteDocumentIndexInboundPort
    update_document_folder_relations: UpdateDocumentFolderRelationsInboundPort
    index_folder: IndexFolderInboundPort
    delete_folder_index: DeleteFolderIndexInboundPort
    run_task: RunTaskInboundPort
    get_task: GetTaskInboundPort
    remove_task_input: RemoveTaskInputInboundPort
    record_action_result: RecordActionResultInboundPort
