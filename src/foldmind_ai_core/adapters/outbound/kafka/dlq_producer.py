# mypy: disable-error-code=import-not-found

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class KafkaDlqProducer:
    bootstrap_servers: str
    extra_config: dict[str, Any] = field(default_factory=dict)
    _producer: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        from confluent_kafka import Producer

        self._producer = Producer(
            {
                "bootstrap.servers": self.bootstrap_servers,
                **self.extra_config,
            }
        )

    def publish(
        self,
        *,
        topic: str,
        key: bytes | str | None,
        value: dict[str, Any],
        headers: tuple[tuple[str, bytes | str | None], ...] = (),
    ) -> None:
        self._producer.produce(
            topic=topic,
            key=_key_bytes(key),
            value=json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8"),
            headers=list(headers),
        )
        self._producer.flush()

    def close(self) -> None:
        self._producer.flush()


def _key_bytes(key: bytes | str | None) -> bytes | None:
    if key is None:
        return None
    if isinstance(key, bytes):
        return key
    return key.encode("utf-8")
