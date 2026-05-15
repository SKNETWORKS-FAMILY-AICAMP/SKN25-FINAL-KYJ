from __future__ import annotations

import base64
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from foldmind_ai_core.adapters.inbound.messaging.broker import (
    BrokerConsumer,
    BrokerMessage,
)
from foldmind_ai_core.adapters.inbound.messaging.dispatcher import OutboxEventDispatcher
from foldmind_ai_core.adapters.inbound.messaging.message_codec import (
    outbox_event_from_flattened_payload,
    outbox_event_key,
)
from foldmind_ai_core.domain.indexing.outbox import OutboxEvent

logger = logging.getLogger(__name__)


class DlqProducer(Protocol):
    def publish(
        self,
        *,
        topic: str,
        key: bytes | str | None,
        value: dict[str, Any],
        headers: tuple[tuple[str, bytes | str | None], ...] = (),
    ) -> None:
        ...

    def close(self) -> None:
        ...


class OutboxFreshnessStore(Protocol):
    def latest_sequence_for(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
    ) -> int | None:
        ...


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_retries: int = 3
    backoff_seconds: float = 1.0

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries must be greater than or equal to 0.")
        if self.backoff_seconds < 0:
            raise ValueError("backoff_seconds must be greater than or equal to 0.")

    def delay_for_retry(self, retry_number: int) -> float:
        return float(self.backoff_seconds * (2 ** max(0, retry_number - 1)))


@dataclass(slots=True)
class OutboxMessageProcessor:
    dispatcher: OutboxEventDispatcher
    freshness_store: OutboxFreshnessStore
    dlq_producer: DlqProducer
    dlq_topic: str
    projection_target: str | None = None
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    sleep: Callable[[float], None] | None = None

    def process(self, message: BrokerMessage, consumer: BrokerConsumer) -> None:
        last_error: Exception | None = None
        for attempt_index in range(self.retry_policy.max_retries + 1):
            try:
                event = outbox_event_from_flattened_payload(message.value)
                if self._is_stale(event):
                    consumer.commit(message)
                    return
                self.dispatcher.handle_outbox_event(event)
                consumer.commit(message)
                return
            except Exception as exc:
                last_error = exc
                if attempt_index >= self.retry_policy.max_retries:
                    break
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
                self._sleep(delay)

        assert last_error is not None
        self._publish_dlq(message, last_error)
        consumer.commit(message)

    def _sleep(self, seconds: float) -> None:
        if self.sleep is not None:
            self.sleep(seconds)
            return
        if seconds <= 0:
            return
        import time

        time.sleep(seconds)

    def _publish_dlq(self, message: BrokerMessage, error: Exception) -> None:
        self.dlq_producer.publish(
            topic=self.dlq_topic,
            key=_message_key(message),
            value=_dlq_payload(
                message,
                error,
                attempts=self.retry_policy.max_retries + 1,
                projection_target=self.projection_target,
            ),
            headers=message.headers,
        )

    def _is_stale(self, event: OutboxEvent) -> bool:
        if event.sequence is None:
            raise ValueError("Outbox message is missing required field: sequence.")
        latest_sequence = self.freshness_store.latest_sequence_for(
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
        )
        if latest_sequence is None:
            raise RuntimeError(
                "Cannot determine latest outbox sequence for "
                f"{event.aggregate_type}:{event.aggregate_id}."
            )
        return event.sequence < latest_sequence


@dataclass(slots=True)
class OutboxWorkerRuntime:
    consumer: BrokerConsumer
    processor: OutboxMessageProcessor
    poll_timeout_seconds: float = 1.0

    def run_once(self) -> bool:
        message = self.consumer.poll(self.poll_timeout_seconds)
        if message is None:
            return False
        self.processor.process(message, self.consumer)
        return True

    def run_forever(self) -> None:
        try:
            while True:
                self.run_once()
        finally:
            self.close()

    def close(self) -> None:
        self.processor.dlq_producer.close()
        self.consumer.close()


def _message_key(message: BrokerMessage) -> bytes | str | None:
    if message.key is not None:
        return message.key
    try:
        event = outbox_event_from_flattened_payload(message.value)
    except Exception:
        return None
    return outbox_event_key(event)


def _dlq_payload(
    message: BrokerMessage,
    error: Exception,
    *,
    attempts: int,
    projection_target: str | None = None,
) -> dict[str, Any]:
    event: OutboxEvent | None
    try:
        event = outbox_event_from_flattened_payload(message.value)
    except Exception:
        event = None
    payload: dict[str, Any] = {
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


def _event_metadata(event: OutboxEvent | None) -> dict[str, Any] | None:
    if event is None:
        return None
    return {
        "id": event.id,
        "sequence": event.sequence,
        "event_key": event.event_key,
        "aggregate_type": event.aggregate_type,
        "aggregate_id": event.aggregate_id,
        "event_type": event.event_type,
        "event_schema_version": event.event_schema_version,
    }


def _safe_value(value: bytes | str | None) -> Any:
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


def _json_or_text(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value
