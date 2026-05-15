from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class BrokerMessage:
    value: bytes | str
    key: bytes | str | None = None
    topic: str = ""
    partition: int | None = None
    offset: int | None = None
    headers: tuple[tuple[str, bytes | str | None], ...] = field(default_factory=tuple)
    raw: Any | None = None


class BrokerConsumer(Protocol):
    def poll(self, timeout_seconds: float) -> BrokerMessage | None:
        ...

    def commit(self, message: BrokerMessage) -> None:
        ...

    def close(self) -> None:
        ...
