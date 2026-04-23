from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class HostActionStatus(StrEnum):
    PROPOSED = "proposed"
    READY = "ready"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class HostActionResultType(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRY = "retry"
    SKIPPED = "skipped"


@dataclass(slots=True)
class HostActionPolicy:
    max_attempts: int = 1
    allow_skip: bool = False
    retryable: bool = False
    requires_confirmation: bool = True


@dataclass(slots=True)
class HostAction:
    action_type: str
    summary: str
    action_id: str | None = None
    reason: str = ""
    status: HostActionStatus = HostActionStatus.PROPOSED
    input: dict[str, Any] | None = None
    attempts: int = 0
    depends_on: list[str] = field(default_factory=list)
    policy: HostActionPolicy = field(default_factory=HostActionPolicy)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class HostActionResult:
    action_id: str
    action_type: str | None = None
    outcome: HostActionResultType = HostActionResultType.SUCCEEDED
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ActionPlan:
    summary: str
    steps: list[str]
    host_actions: list[HostAction] = field(default_factory=list)
