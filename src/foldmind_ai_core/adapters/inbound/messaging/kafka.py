# mypy: disable-error-code=import-not-found

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .broker import BrokerMessage


@dataclass(slots=True)
class KafkaOutboxConsumer:
    bootstrap_servers: str
    topic: str
    group_id: str
    auto_offset_reset: str = "earliest"
    extra_config: dict[str, Any] = field(default_factory=dict)
    _consumer: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        from confluent_kafka import Consumer

        self._consumer = Consumer(
            {
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": self.group_id,
                "enable.auto.commit": False,
                "auto.offset.reset": self.auto_offset_reset,
                **self.extra_config,
            }
        )
        self._consumer.subscribe([self.topic])

    def poll(self, timeout_seconds: float) -> BrokerMessage | None:
        kafka_message = self._consumer.poll(timeout_seconds)
        if kafka_message is None:
            return None
        error = kafka_message.error()
        if error is not None:
            raise RuntimeError(f"Kafka consumer error: {error}")
        return BrokerMessage(
            key=kafka_message.key(),
            value=kafka_message.value(),
            topic=kafka_message.topic(),
            partition=kafka_message.partition(),
            offset=kafka_message.offset(),
            headers=tuple(kafka_message.headers() or ()),
            raw=kafka_message,
        )

    def commit(self, message: BrokerMessage) -> None:
        if message.raw is None:
            raise ValueError("Cannot commit a Kafka message without the raw handle.")
        self._consumer.commit(message=message.raw, asynchronous=False)

    def close(self) -> None:
        self._consumer.close()
