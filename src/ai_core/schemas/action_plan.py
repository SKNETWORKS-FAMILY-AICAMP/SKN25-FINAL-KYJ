from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ActionPlan:
    summary: str
    steps: list[str]
