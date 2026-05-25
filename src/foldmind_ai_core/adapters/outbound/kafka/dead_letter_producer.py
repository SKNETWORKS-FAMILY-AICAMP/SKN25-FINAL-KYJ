# mypy: disable-error-code=import-not-found

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from foldmind_ai_core.core.application.errors import ProviderCallError
from foldmind_ai_core.shared.types import JsonObject


@dataclass(slots=True)
class KafkaDeadLetterProducer:
    bootstrap_servers: str
    extra_config: dict[str, Any] = field(default_factory=dict)
    _producer: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            from confluent_kafka import Producer

            self._producer = Producer(
                {
                    "bootstrap.servers": self.bootstrap_servers,
                    **self.extra_config,
                }
            )
        except Exception as exc:
            raise ProviderCallError("Kafka dead-letter producer setup failed.") from exc

    def publish(
        self,
        *,
        topic: str,
        key: bytes | str | None,
        value: JsonObject,
        headers: tuple[tuple[str, bytes | str | None], ...] = (),
    ) -> None:
        key_bytes = key if key is None or isinstance(key, bytes) else key.encode("utf-8")
        try:
            self._producer.produce(
                topic=topic,
                key=key_bytes,
                value=json.dumps(value, ensure_ascii=False, sort_keys=True).encode(
                    "utf-8"
                ),
                headers=list(headers),
            )
            self._producer.flush()
        except Exception as exc:
            raise ProviderCallError("Kafka dead-letter publish failed.") from exc

    def close(self) -> None:
        try:
            self._producer.flush()
        except Exception as exc:
            raise ProviderCallError("Kafka dead-letter producer close failed.") from exc
