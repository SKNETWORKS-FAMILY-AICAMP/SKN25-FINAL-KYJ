from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.domain.models.document_index_state import DocumentIndexState
from foldmind_ai_core.core.domain.models.document_sources import DocumentSourceState
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.shared.input_digest import input_digest

_FOLDER_SOURCE_PROJECTION_POLICY_VERSION = "1"


@dataclass(frozen=True, slots=True)
class FolderProjectionDigestService:
    def folder_index_input_digest(
        self,
        *,
        folder_id: str,
        folder: SourceFolder | None,
    ) -> str:
        if folder is None:
            return input_digest(
                "folder_index",
                {
                    "folder_id": folder_id,
                    "source_missing": True,
                    "projection_policy_version": _FOLDER_SOURCE_PROJECTION_POLICY_VERSION,
                },
            )
        return input_digest(
            "folder_index",
            {
                "folder_id": folder_id,
                "name": folder.name,
                "path": folder.path,
                "parent_folder_id": folder.parent_folder_id,
                "description": folder.description,
                "metadata": dict(folder.metadata),
                "projection_policy_version": _FOLDER_SOURCE_PROJECTION_POLICY_VERSION,
            },
        )

    def folder_signal_input_digest(
        self,
        *,
        document_sources: tuple[DocumentSourceState, ...],
        document_index_states: tuple[DocumentIndexState, ...],
        folder_index_input_digest: str,
        signal_generation_version: str,
    ) -> str:
        index_states_by_document_id = {
            state.document_id: state for state in document_index_states
        }
        members: list[dict[str, str]] = []
        for source in sorted(document_sources, key=lambda item: item.document_id):
            index_state = index_states_by_document_id.get(source.document_id)
            members.append(
                {
                    "document_id": source.document_id,
                    "content_digest": source.content_digest,
                    "document_index_input_digest": (
                        index_state.document_index_input_digest
                        if index_state is not None
                        else ""
                    ),
                    "document_signal_input_digest": (
                        index_state.document_signal_input_digest
                        if index_state is not None
                        else ""
                    ),
                }
            )
        return input_digest(
            "folder_signal",
            {
                "folder_index_input_digest": folder_index_input_digest,
                "members": members,
                "signal_generation_version": signal_generation_version,
            },
        )
