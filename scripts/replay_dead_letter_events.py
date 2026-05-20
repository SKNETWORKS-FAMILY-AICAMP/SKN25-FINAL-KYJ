from __future__ import annotations

import argparse
import base64
import json
from typing import cast

from confluent_kafka import Consumer, Producer

from foldmind_ai_core.bootstrap.settings import load_settings
from foldmind_ai_core.shared.types import JsonObject, JsonValue


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay outbox dead-letter messages.")
    parser.add_argument("--max-messages", type=int, default=100)
    parser.add_argument("--timeout-seconds", type=float, default=1.0)
    args = parser.parse_args()

    settings = load_settings()
    consumer = Consumer(
        {
            "bootstrap.servers": settings.required_kafka_bootstrap_servers,
            "group.id": "foldmind-ai-core-dead-letter-replay",
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        }
    )
    producer = Producer({"bootstrap.servers": settings.required_kafka_bootstrap_servers})
    consumer.subscribe([settings.kafka_dead_letter_topic])
    replayed = 0
    try:
        while replayed < args.max_messages:
            message = consumer.poll(args.timeout_seconds)
            if message is None:
                break
            if message.error() is not None:
                raise RuntimeError(f"Kafka consumer error: {message.error()}")
            payload = _json_object(message.value())
            original = _required_json_object(payload, "original")
            producer.produce(
                topic=settings.kafka_outbox_topic,
                key=_wire_value(original.get("key")),
                value=_wire_value(original["value"]),
                headers=[
                    (str(header["key"]), _wire_value(header.get("value")))
                    for header in _json_object_items(original.get("headers"))
                    if "key" in header
                ],
            )
            producer.flush()
            consumer.commit(message=message, asynchronous=False)
            replayed += 1
    finally:
        consumer.close()
        producer.flush()
    print(f"Replayed {replayed} dead-letter message(s).")


def _json_object(value: bytes) -> JsonObject:
    parsed = json.loads(value.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Dead-letter message value must be a JSON object.")
    return cast(JsonObject, parsed)


def _required_json_object(payload: JsonObject, name: str) -> JsonObject:
    value = payload[name]
    if not isinstance(value, dict):
        raise ValueError(f"Dead-letter payload field {name} must be a JSON object.")
    return value


def _json_object_items(value: JsonValue | None) -> tuple[JsonObject, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(item for item in value if isinstance(item, dict))


def _wire_value(value: JsonValue | None) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, dict) and value.get("encoding") == "base64":
        return base64.b64decode(str(value["value"]))
    if isinstance(value, str):
        return value.encode("utf-8")
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")


if __name__ == "__main__":
    main()
