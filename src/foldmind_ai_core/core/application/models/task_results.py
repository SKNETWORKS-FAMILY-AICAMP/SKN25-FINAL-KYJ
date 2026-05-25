from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.domain.models.tasks import TaskSnapshot


@dataclass(frozen=True, slots=True)
class RecordActionResult:
    recorded: bool
    task: TaskSnapshot
