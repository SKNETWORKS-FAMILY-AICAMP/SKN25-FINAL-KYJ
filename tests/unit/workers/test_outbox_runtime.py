from __future__ import annotations

import json
import unittest

from foldmind_ai_core.adapters.inbound.messaging.broker import BrokerMessage
from foldmind_ai_core.workers.outbox_runtime import (
    OutboxMessageProcessor,
    RetryPolicy,
)


class FakeBrokerConsumer:
    def __init__(self) -> None:
        self.committed: list[BrokerMessage] = []

    def poll(self, timeout_seconds: float) -> BrokerMessage | None:
        return None

    def commit(self, message: BrokerMessage) -> None:
        self.committed.append(message)

    def close(self) -> None:
        pass


class FakeDlqProducer:
    def __init__(self) -> None:
        self.published: list[tuple[str, bytes | str | None, dict[str, object]]] = []

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
        pass


class FakeFreshnessStore:
    def __init__(self, latest_sequence: int = 10, *, fail: bool = False) -> None:
        self.latest_sequence = latest_sequence
        self.fail = fail
        self.calls: list[tuple[str, str]] = []

    def latest_sequence_for(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
    ) -> int | None:
        self.calls.append((aggregate_type, aggregate_id))
        if self.fail:
            raise RuntimeError("freshness unavailable")
        return self.latest_sequence


class FakeDispatcher:
    def __init__(self, *, failures_before_success: int = 0) -> None:
        self.failures_before_success = failures_before_success
        self.events: list[object] = []

    def handle_outbox_event(self, event: object) -> None:
        self.events.append(event)
        if len(self.events) <= self.failures_before_success:
            raise RuntimeError("projection failed")


class OutboxRuntimeTests(unittest.TestCase):
    def test_message_processor_commits_after_successful_projection(self) -> None:
        consumer = FakeBrokerConsumer()
        dlq = FakeDlqProducer()
        dispatcher = FakeDispatcher()
        message = _flattened_broker_message()

        OutboxMessageProcessor(
            dispatcher=dispatcher,  # type: ignore[arg-type]
            freshness_store=FakeFreshnessStore(),
            dlq_producer=dlq,
            dlq_topic="indexing-events.dlq",
            retry_policy=RetryPolicy(max_retries=3, backoff_seconds=0),
        ).process(message, consumer)

        self.assertEqual(consumer.committed, [message])
        self.assertEqual(len(dlq.published), 0)
        self.assertEqual(len(dispatcher.events), 1)

    def test_message_processor_does_not_commit_before_retry_succeeds(self) -> None:
        consumer = FakeBrokerConsumer()
        dlq = FakeDlqProducer()
        dispatcher = FakeDispatcher(failures_before_success=1)
        committed_during_sleep: list[int] = []

        OutboxMessageProcessor(
            dispatcher=dispatcher,  # type: ignore[arg-type]
            freshness_store=FakeFreshnessStore(),
            dlq_producer=dlq,
            dlq_topic="indexing-events.dlq",
            retry_policy=RetryPolicy(max_retries=2, backoff_seconds=0),
            sleep=lambda _seconds: committed_during_sleep.append(len(consumer.committed)),
        ).process(_flattened_broker_message(), consumer)

        self.assertEqual(committed_during_sleep, [0])
        self.assertEqual(len(consumer.committed), 1)
        self.assertEqual(len(dlq.published), 0)
        self.assertEqual(len(dispatcher.events), 2)

    def test_message_processor_publishes_dlq_and_commits_after_retry_exhaustion(
        self,
    ) -> None:
        consumer = FakeBrokerConsumer()
        dlq = FakeDlqProducer()
        dispatcher = FakeDispatcher(failures_before_success=10)
        message = _flattened_broker_message()

        OutboxMessageProcessor(
            dispatcher=dispatcher,  # type: ignore[arg-type]
            freshness_store=FakeFreshnessStore(),
            dlq_producer=dlq,
            dlq_topic="indexing-events.dlq",
            projection_target="neo4j-graph",
            retry_policy=RetryPolicy(max_retries=1, backoff_seconds=0),
        ).process(message, consumer)

        self.assertEqual(consumer.committed, [message])
        self.assertEqual(len(dlq.published), 1)
        topic, key, value = dlq.published[0]
        self.assertEqual(topic, "indexing-events.dlq")
        self.assertEqual(key, b"DOCUMENT:doc-1")
        self.assertEqual(value["attempts"], 2)
        self.assertEqual(value["projection_target"], "neo4j-graph")
        self.assertEqual(value["event"]["event_type"], "DOCUMENT_DELETED")
        self.assertEqual(value["event"]["sequence"], 10)
        self.assertEqual(value["event"]["event_key"], "DOCUMENT:doc-1")

    def test_message_processor_commits_stale_event_without_projection(self) -> None:
        consumer = FakeBrokerConsumer()
        dlq = FakeDlqProducer()
        dispatcher = FakeDispatcher()
        message = _flattened_broker_message(sequence=9)

        OutboxMessageProcessor(
            dispatcher=dispatcher,  # type: ignore[arg-type]
            freshness_store=FakeFreshnessStore(latest_sequence=10),
            dlq_producer=dlq,
            dlq_topic="indexing-events.dlq",
            retry_policy=RetryPolicy(max_retries=0, backoff_seconds=0),
        ).process(message, consumer)

        self.assertEqual(consumer.committed, [message])
        self.assertEqual(dispatcher.events, [])
        self.assertEqual(dlq.published, [])

    def test_message_processor_retries_when_freshness_check_fails(self) -> None:
        consumer = FakeBrokerConsumer()
        dlq = FakeDlqProducer()
        dispatcher = FakeDispatcher()
        message = _flattened_broker_message()

        OutboxMessageProcessor(
            dispatcher=dispatcher,  # type: ignore[arg-type]
            freshness_store=FakeFreshnessStore(fail=True),
            dlq_producer=dlq,
            dlq_topic="indexing-events.dlq",
            retry_policy=RetryPolicy(max_retries=1, backoff_seconds=0),
        ).process(message, consumer)

        self.assertEqual(consumer.committed, [message])
        self.assertEqual(dispatcher.events, [])
        self.assertEqual(len(dlq.published), 1)
        self.assertEqual(dlq.published[0][2]["error"]["message"], "freshness unavailable")


def _flattened_broker_message(*, sequence: int = 10) -> BrokerMessage:
    return BrokerMessage(
        key=b"DOCUMENT:doc-1",
        topic="indexing-events",
        partition=0,
        offset=10,
        value=json.dumps(
            {
                "id": "11111111-1111-4111-8111-111111111111",
                "sequence": sequence,
                "event_key": "DOCUMENT:doc-1",
                "aggregate_type": "DOCUMENT",
                "aggregate_id": "doc-1",
                "event_type": "DOCUMENT_DELETED",
                "event_schema_version": "1",
                "payload": {
                    "document_id": "doc-1",
                },
            }
        ).encode("utf-8"),
    )


if __name__ == "__main__":
    unittest.main()
