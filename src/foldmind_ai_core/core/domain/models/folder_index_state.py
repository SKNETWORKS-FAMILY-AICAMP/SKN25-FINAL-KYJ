from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FolderSignalRefreshStatus(StrEnum):
    EMPTY = "empty"
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class FolderIndexState:
    folder_id: str
    folder_index_input_digest: str
    folder_signal_input_digest: str
    signal_generation_version: str = "1"
    folder_signal_refresh_status: FolderSignalRefreshStatus = (
        FolderSignalRefreshStatus.EMPTY
    )
