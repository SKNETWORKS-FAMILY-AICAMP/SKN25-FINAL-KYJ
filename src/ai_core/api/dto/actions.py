from __future__ import annotations

from dataclasses import dataclass

from ai_core.domain.actions import HostActionResult


@dataclass(slots=True)
class RecordHostActionResultRequest:
    tenant: str
    task_id: str
    result: HostActionResult
