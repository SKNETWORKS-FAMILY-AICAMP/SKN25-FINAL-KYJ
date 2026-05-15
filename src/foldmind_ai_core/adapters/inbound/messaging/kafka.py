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

        self._consumer = Consumer(self._consumer_config())
        self._consumer.subscribe([self.topic])

    def poll(self, timeout_seconds: float) -> BrokerMessage | None:
        kafka_message = self._consumer.poll(timeout_seconds)
        if kafka_message is None:
            return None
        error = kafka_message.error()
        if error is not None:
            raise RuntimeError(f"Kafka consumer error: {error}")
        return _broker_message_from_kafka(kafka_message)

    def commit(self, message: BrokerMessage) -> None:
        if message.raw is None:
            raise ValueError("Cannot commit a Kafka message without the raw handle.")
        self._consumer.commit(message=message.raw, asynchronous=False)

    def close(self) -> None:
        self._consumer.close()

    def _consumer_config(self) -> dict[str, Any]:
        return {
            "bootstrap.servers": self.bootstrap_servers,
            "group.id": self.group_id,
            "enable.auto.commit": False,
            "auto.offset.reset": self.auto_offset_reset,
            **self.extra_config,
        }


def _broker_message_from_kafka(message: Any) -> BrokerMessage:
    return BrokerMessage(
        key=message.key(),
        value=message.value(),
        topic=message.topic(),
        partition=message.partition(),
        offset=message.offset(),
        headers=tuple(message.headers() or ()),
        raw=message,
    )
