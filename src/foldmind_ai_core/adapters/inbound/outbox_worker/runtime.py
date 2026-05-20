from __future__ import annotations

import base64
import json
import logging
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, cast

from foldmind_ai_core.adapters.inbound.messaging.broker import (
    BrokerConsumer,
    BrokerMessage,
)
from foldmind_ai_core.adapters.inbound.messaging.dispatcher import OutboxEventConsumer
from foldmind_ai_core.adapters.inbound.messaging.message_codec import (
    outbox_event_from_flattened_payload,
)
from foldmind_ai_core.core.domain.models.indexing.outbox import OutboxEvent
from foldmind_ai_core.shared.types import JsonObject, JsonValue

logger = logging.getLogger(__name__)


class DeadLetterProducer(Protocol):
    def publish(
        self,
        *,
        topic: str,
        key: bytes | str | None,
        value: JsonObject,
        headers: tuple[tuple[str, bytes | str | None], ...] = (),
    ) -> None:
        ...

    def close(self) -> None:
        ...


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_retries: int = 3
    backoff_seconds: float = 1.0

    def __post_init__(self) -> None:
        if isinstance(self.max_retries, bool) or not isinstance(self.max_retries, int):
            raise ValueError("max_retries must be an integer.")
        if self.max_retries < 0:
            raise ValueError("max_retries must be greater than or equal to 0.")
        if isinstance(self.backoff_seconds, bool) or not isinstance(
            self.backoff_seconds, int | float
        ):
            raise ValueError("backoff_seconds must be numeric.")
        if not math.isfinite(float(self.backoff_seconds)) or self.backoff_seconds < 0:
            raise ValueError("backoff_seconds must be greater than or equal to 0.")

    def delay_for_retry(self, retry_number: int) -> float:
        return float(self.backoff_seconds * (2 ** max(0, retry_number - 1)))


@dataclass(slots=True)
class OutboxProjectionMessageConsumer:
    dispatcher: OutboxEventConsumer
    dead_letter_producer: DeadLetterProducer
    dead_letter_topic: str
    projection_target: str | None = None
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    sleep: Callable[[float], None] | None = None

    def process(self, message: BrokerMessage, consumer: BrokerConsumer) -> None:
        for attempt_index in range(self.retry_policy.max_retries + 1):
            try:
                event = outbox_event_from_flattened_payload(message.value)
                self.dispatcher.consume_outbox_event(event)
                consumer.commit(message)
                return
            except Exception as exc:
                if attempt_index >= self.retry_policy.max_retries:
                    self.dead_letter_producer.publish(
                        topic=self.dead_letter_topic,
                        key=_message_key(message),
                        value=_dead_letter_payload(
                            message,
                            exc,
                            attempts=self.retry_policy.max_retries + 1,
                            projection_target=self.projection_target,
                        ),
                        headers=message.headers,
                    )
                    consumer.commit(message)
                    return
                delay = self.retry_policy.delay_for_retry(attempt_index + 1)
                logger.warning(
                    "Outbox projection failed; retrying.",
                    extra={
                        "attempt": attempt_index + 1,
                        "delay_seconds": delay,
                        "topic": message.topic,
                        "partition": message.partition,
                        "offset": message.offset,
                    },
                    exc_info=True,
                )
                if self.sleep is not None:
                    self.sleep(delay)
                elif delay > 0:
                    import time

                    time.sleep(delay)


@dataclass(slots=True)
class OutboxWorkerRuntime:
    consumer: BrokerConsumer
    message_consumer: OutboxProjectionMessageConsumer
    poll_timeout_seconds: float = 1.0

    def run_once(self) -> bool:
        message = self.consumer.poll(self.poll_timeout_seconds)
        if message is None:
            return False
        self.message_consumer.process(message, self.consumer)
        return True

    def run_forever(self) -> None:
        try:
            while True:
                self.run_once()
        finally:
            self.close()

    def close(self) -> None:
        self.message_consumer.dead_letter_producer.close()
        self.consumer.close()


def _message_key(message: BrokerMessage) -> bytes | str | None:
    if message.key is not None:
        return message.key
    try:
        event = outbox_event_from_flattened_payload(message.value)
    except Exception:
        return None
    return event.partition_key


def _dead_letter_payload(
    message: BrokerMessage,
    error: Exception,
    *,
    attempts: int,
    projection_target: str | None = None,
) -> JsonObject:
    event: OutboxEvent | None
    try:
        event = outbox_event_from_flattened_payload(message.value)
    except Exception:
        event = None
    payload: JsonObject = {
        "failed_at": datetime.now(UTC).isoformat(),
        "attempts": attempts,
        "error": {
            "type": type(error).__name__,
            "message": str(error),
        },
        "event": _event_metadata(event),
        "original": {
            "topic": message.topic,
            "partition": message.partition,
            "offset": message.offset,
            "key": _safe_value(message.key),
            "value": _safe_value(message.value),
            "headers": [
                {"key": key, "value": _safe_value(value)}
                for key, value in message.headers
            ],
        },
    }
    if projection_target is not None:
        payload["projection_target"] = projection_target
    return payload


def _event_metadata(event: OutboxEvent | None) -> JsonObject | None:
    if event is None:
        return None
    return {
        "event_id": event.event_id,
        "event_sequence": event.event_sequence,
        "partition_key": event.partition_key,
        "source_kind": event.source_kind,
        "source_id": event.source_id,
        "event_type": event.event_type,
        "payload_schema_version": event.payload_schema_version,
        "tenant": event.tenant,
        "idempotency_key": event.idempotency_key,
    }


def _safe_value(value: bytes | str | None) -> JsonValue:
    if value is None:
        return None
    if isinstance(value, str):
        return _json_or_text(value)
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError:
        return {
            "encoding": "base64",
            "value": base64.b64encode(value).decode("ascii"),
        }
    return _json_or_text(text)


def _json_or_text(value: str) -> JsonValue:
    try:
        return cast(JsonValue, json.loads(value))
    except json.JSONDecodeError:
        return value
