from __future__ import annotations

import argparse
import base64
import json
from typing import Any

from confluent_kafka import Consumer, Producer

from foldmind_ai_core.bootstrap.settings import load_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay outbox DLQ messages.")
    parser.add_argument("--max-messages", type=int, default=100)
    parser.add_argument("--timeout-seconds", type=float, default=1.0)
    args = parser.parse_args()

    settings = load_settings()
    consumer = Consumer(
        {
            "bootstrap.servers": settings.required_kafka_bootstrap_servers,
            "group.id": "foldmind-ai-core-dlq-replay",
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        }
    )
    producer = Producer({"bootstrap.servers": settings.required_kafka_bootstrap_servers})
    consumer.subscribe([settings.kafka_dlq_topic])
    replayed = 0
    try:
        while replayed < args.max_messages:
            message = consumer.poll(args.timeout_seconds)
            if message is None:
                break
            if message.error() is not None:
                raise RuntimeError(f"Kafka consumer error: {message.error()}")
            payload = json.loads(message.value().decode("utf-8"))
            original = payload["original"]
            producer.produce(
                topic=settings.kafka_outbox_topic,
                key=_wire_value(original.get("key")),
                value=_wire_value(original["value"]),
                headers=[
                    (header["key"], _wire_value(header.get("value")))
                    for header in original.get("headers", [])
                ],
            )
            producer.flush()
            consumer.commit(message=message, asynchronous=False)
            replayed += 1
    finally:
        consumer.close()
        producer.flush()
    print(f"Replayed {replayed} DLQ message(s).")


def _wire_value(value: Any) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, dict) and value.get("encoding") == "base64":
        return base64.b64decode(str(value["value"]))
    if isinstance(value, str):
        return value.encode("utf-8")
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")


if __name__ == "__main__":
    main()
