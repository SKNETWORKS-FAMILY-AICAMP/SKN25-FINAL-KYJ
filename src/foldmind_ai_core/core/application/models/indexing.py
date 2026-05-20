from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeletedDocumentIdentity:
    tenant: str
    document_id: str
    affected_folder_ids: tuple[str, ...] = ()
    folder_signal_invalidations: tuple["FolderSignalInvalidation", ...] = ()


@dataclass(frozen=True, slots=True)
class DeletedFolderIdentity:
    tenant: str
    folder_id: str


@dataclass(frozen=True, slots=True)
class FolderSignalInvalidation:
    tenant: str
    folder_id: str
    folder_signal_input_revision: int


@dataclass(frozen=True, slots=True)
class DocumentIndexChange:
    applied: bool
    folder_signal_invalidations: tuple[FolderSignalInvalidation, ...] = ()


@dataclass(frozen=True, slots=True)
class FolderIndexChange:
    applied: bool
    folder_signal_invalidation: FolderSignalInvalidation | None = None


@dataclass(frozen=True, slots=True)
class FolderSignalRefreshCommit:
    applied: bool
    folder_signal_input_revision: int


@dataclass(frozen=True, slots=True)
class FolderRelationChange:
    applied: bool
    source_exists: bool = True
    previous_folder_ids: tuple[str, ...] = ()
    current_folder_ids: tuple[str, ...] = ()
    folder_signal_invalidations: tuple[FolderSignalInvalidation, ...] = ()

    @property
    def affected_folder_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    *self.previous_folder_ids,
                    *self.current_folder_ids,
                }
            )
        )


@dataclass(frozen=True, slots=True)
class SourceDocumentFolderRelationSnapshot:
    tenant: str
    document_id: str
    source_version: str
    folder_ids: tuple[str, ...] = ()
