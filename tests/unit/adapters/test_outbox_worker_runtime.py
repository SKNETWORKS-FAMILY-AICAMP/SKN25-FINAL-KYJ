from __future__ import annotations

import json
import unittest

from foldmind_ai_core.adapters.inbound.messaging.broker import BrokerMessage
from foldmind_ai_core.adapters.inbound.outbox_worker.runtime import (
    OutboxProjectionMessageConsumer,
    RetryPolicy,
)


class FakeBrokerConsumer:
    def __init__(self) -> None:
        self.committed: list[BrokerMessage] = []
        self.closed = False

    def poll(self, timeout_seconds: float) -> BrokerMessage | None:
        return None

    def commit(self, message: BrokerMessage) -> None:
        self.committed.append(message)

    def close(self) -> None:
        self.closed = True


class FakeDeadLetterProducer:
    def __init__(self) -> None:
        self.published: list[tuple[str, bytes | str | None, dict[str, object]]] = []
        self.closed = False

    def publish(
        self,
        *,
        topic: str,
        key: bytes | str | None,
        value: dict[str, object],
        headers: tuple[tuple[str, bytes | str | None], ...] = (),
    ) -> None:
        self.published.append((topic, key, value))

    def close(self) -> None:
        self.closed = True


class FakeDispatcher:
    def __init__(self, *, failures_before_success: int = 0) -> None:
        self.failures_before_success = failures_before_success
        self.events: list[object] = []

    async def consume_outbox_event(self, event: object) -> None:
        self.events.append(event)
        if len(self.events) <= self.failures_before_success:
            raise RuntimeError("projection failed")


class OutboxRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def test_retry_policy_rejects_non_finite_backoff(self) -> None:
        with self.assertRaises(ValueError):
            RetryPolicy(max_retries=1, backoff_seconds=float("nan"))
        with self.assertRaises(ValueError):
            RetryPolicy(max_retries=True, backoff_seconds=0)

    async def test_projection_message_consumer_commits_after_successful_projection(
        self,
    ) -> None:
        consumer = FakeBrokerConsumer()
        dead_letter = FakeDeadLetterProducer()
        dispatcher = FakeDispatcher()
        message = _flattened_broker_message()

        await OutboxProjectionMessageConsumer(
            dispatcher=dispatcher,
            dead_letter_producer=dead_letter,
            dead_letter_topic="indexing-events.dlq",
            retry_policy=RetryPolicy(max_retries=3, backoff_seconds=0),
        ).process(message, consumer)

        self.assertEqual(consumer.committed, [message])
        self.assertEqual(len(dead_letter.published), 0)
        self.assertEqual(len(dispatcher.events), 1)

    async def test_projection_message_consumer_does_not_commit_before_retry_succeeds(
        self,
    ) -> None:
        consumer = FakeBrokerConsumer()
        dead_letter = FakeDeadLetterProducer()
        dispatcher = FakeDispatcher(failures_before_success=1)
        committed_during_sleep: list[int] = []

        await OutboxProjectionMessageConsumer(
            dispatcher=dispatcher,
            dead_letter_producer=dead_letter,
            dead_letter_topic="indexing-events.dlq",
            retry_policy=RetryPolicy(max_retries=2, backoff_seconds=0),
            sleep=lambda _seconds: committed_during_sleep.append(len(consumer.committed)),
        ).process(_flattened_broker_message(), consumer)

        self.assertEqual(committed_during_sleep, [0])
        self.assertEqual(len(consumer.committed), 1)
        self.assertEqual(len(dead_letter.published), 0)
        self.assertEqual(len(dispatcher.events), 2)

    async def test_projection_message_consumer_dead_letters_after_retry_exhaustion(
        self,
    ) -> None:
        consumer = FakeBrokerConsumer()
        dead_letter = FakeDeadLetterProducer()
        dispatcher = FakeDispatcher(failures_before_success=10)
        message = _flattened_broker_message()

        await OutboxProjectionMessageConsumer(
            dispatcher=dispatcher,
            dead_letter_producer=dead_letter,
            dead_letter_topic="indexing-events.dlq",
            projection_target="neo4j-graph",
            retry_policy=RetryPolicy(max_retries=1, backoff_seconds=0),
        ).process(message, consumer)

        self.assertEqual(consumer.committed, [message])
        self.assertEqual(len(dead_letter.published), 1)
        topic, key, value = dead_letter.published[0]
        self.assertEqual(topic, "indexing-events.dlq")
        self.assertEqual(key, b"document:tenant-1:doc-1")
        self.assertEqual(value["attempts"], 2)
        self.assertEqual(value["projection_target"], "neo4j-graph")
        self.assertEqual(value["event"]["event_type"], "DOCUMENT_DELETED")
        self.assertEqual(value["event"]["event_sequence"], 10)
        self.assertEqual(
            value["event"]["partition_key"],
            "document:tenant-1:doc-1",
        )
        self.assertEqual(value["event"]["tenant"], "tenant-1")


def _flattened_broker_message(*, event_sequence: int = 10) -> BrokerMessage:
    return BrokerMessage(
        key=b"document:tenant-1:doc-1",
        topic="indexing-events",
        partition=0,
        offset=10,
        value=json.dumps(
            {
                "event_id": "11111111-1111-4111-8111-111111111111",
                "event_sequence": event_sequence,
                "tenant_id": "tenant-1",
                "partition_key": "document:tenant-1:doc-1",
                "source_kind": "document",
                "source_id": "doc-1",
                "event_type": "DOCUMENT_DELETED",
                "payload_schema_version": 1,
                "idempotency_key": "document-delete:tenant-1:doc-1",
                "payload": {
                    "tenant": "tenant-1",
                    "document_id": "doc-1",
                },
            }
        ).encode("utf-8"),
    )


if __name__ == "__main__":
    unittest.main()
