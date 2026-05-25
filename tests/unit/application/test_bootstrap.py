from __future__ import annotations

import unittest
from os import environ
from pathlib import Path
from unittest.mock import patch

from dependency_injector import providers
from pydantic import ValidationError

from foldmind_ai_core.adapters.inbound.messaging.broker import BrokerMessage
from foldmind_ai_core.adapters.inbound.outbox_worker.runtime import (
    OutboxWorkerRuntime,
)
from foldmind_ai_core.bootstrap.api_services import APIApplicationServices
from foldmind_ai_core.bootstrap.container.application import ApplicationContainer
from foldmind_ai_core.bootstrap.container.outbox_worker import OutboxWorkerContainer
from foldmind_ai_core.bootstrap.settings import APISettings, OutboxProjectionTarget

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "src").exists()
)
PACKAGE_ROOT = PROJECT_ROOT / "src" / "foldmind_ai_core"


class FakeBrokerConsumer:
    def poll(self, timeout_seconds: float) -> BrokerMessage | None:
        return None

    def commit(self, message: BrokerMessage) -> None:
        return None

    def close(self) -> None:
        return None


class FakeDeadLetterProducer:
    def publish(
        self,
        *,
        topic: str,
        key: bytes | str | None,
        value: dict[str, object],
        headers: tuple[tuple[str, bytes | str | None], ...] = (),
    ) -> None:
        return None

    def close(self) -> None:
        return None


class FakeOutboxDispatcher:
    async def consume_outbox_event(self, event: object) -> None:
        return None


class BootstrapContainerTests(unittest.TestCase):
    def test_settings_reads_unprefixed_purge_after_days(self) -> None:
        with patch.dict(environ, {"PURGE_AFTER_DAYS": "14"}, clear=True):
            settings = APISettings(_env_file=None)

        self.assertEqual(settings.purge_after_days, 14)

    def test_settings_rejects_invalid_purge_after_days(self) -> None:
        with patch.dict(environ, {"PURGE_AFTER_DAYS": "0"}, clear=True):
            with self.assertRaises(ValidationError):
                APISettings(_env_file=None)

    def test_application_container_builds_fastapi_app_from_overridden_application_services(
        self,
    ) -> None:
        application_services = APIApplicationServices(
            document_indexing=object(),
            folder_indexing=object(),
            task_workflow=object(),
        )

        container = ApplicationContainer()
        container.api_services.override(providers.Object(application_services))

        app = container.fastapi_app()

        self.assertEqual(app.title, "FoldMind AI Core")
        self.assertTrue(any(route.path == "/health" for route in app.routes))

    def test_outbox_worker_container_builds_runtime_from_overridden_edges(self) -> None:
        settings = APISettings(
            kafka_bootstrap_servers="localhost:9092",
            outbox_projection_target=OutboxProjectionTarget.NEO4J_GRAPH,
        )
        container = OutboxWorkerContainer()
        container.settings.override(providers.Object(settings))
        container.kafka_consumer.override(providers.Object(FakeBrokerConsumer()))
        container.dead_letter_producer.override(
            providers.Object(FakeDeadLetterProducer())
        )
        container.dispatcher.override(providers.Object(FakeOutboxDispatcher()))

        runtime = container.runtime()

        self.assertIsInstance(runtime, OutboxWorkerRuntime)

    def test_retired_bootstrap_builder_entrypoints_are_removed(self) -> None:
        removed_files = (
            PACKAGE_ROOT / "bootstrap" / "configured_app.py",
            PACKAGE_ROOT / "bootstrap" / "container" / ("use_" + "cases.py"),
        )
        for path in removed_files:
            self.assertFalse(path.exists(), f"{path} should not exist.")

        forbidden_symbols = (
            "build_application_storage",
            "build_outbox_projection_storage",
            "build_application_" + "use_" + "cases",
            "build_configured_app",
            "build_outbox_worker",
        )
        for path in (PACKAGE_ROOT / "bootstrap").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for symbol in forbidden_symbols:
                self.assertNotIn(symbol, text, f"{symbol} should be removed from {path}.")


if __name__ == "__main__":
    unittest.main()
