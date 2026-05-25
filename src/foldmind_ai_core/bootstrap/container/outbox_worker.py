from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress

from dependency_injector import containers, providers

from foldmind_ai_core.adapters.inbound.messaging.kafka import KafkaOutboxConsumer
from foldmind_ai_core.adapters.inbound.outbox_worker.runtime import (
    OutboxProjectionMessageConsumer,
    OutboxWorkerRuntime,
    RetryPolicy,
)
from foldmind_ai_core.adapters.outbound.kafka.dead_letter_producer import (
    KafkaDeadLetterProducer,
)
from foldmind_ai_core.adapters.outbound.postgres.client import PostgresClient
from foldmind_ai_core.adapters.outbound.postgres.projection_ledger_session import (
    PostgresProjectionLedgerSessionProvider,
)
from foldmind_ai_core.adapters.outbound.postgres.settings import PostgresSettings
from foldmind_ai_core.adapters.outbound.postgres.source_freshness_checker import (
    PostgresSourceFreshnessChecker,
)
from foldmind_ai_core.bootstrap.container.dependencies import (
    AIProviders,
    OutboxProjectionStorage,
)
from foldmind_ai_core.bootstrap.container.lifecycle import (
    ShutdownCallback,
    shutdown_callbacks_for,
)
from foldmind_ai_core.bootstrap.container.outbox import _build_outbox_dispatcher
from foldmind_ai_core.bootstrap.container.providers import _build_ai_providers
from foldmind_ai_core.bootstrap.container.storage import (
    _build_neo4j_store,
    _build_qdrant_document_chunk_vector_store,
    _build_qdrant_document_vector_store,
    _build_qdrant_folder_vector_store,
    _build_qdrant_signal_vector_store,
)
from foldmind_ai_core.bootstrap.observability import (
    TracedOutboxConsumer,
    TracedTransactionProvider,
)
from foldmind_ai_core.bootstrap.settings import APISettings, OutboxProjectionTarget


def _kafka_consumer(settings: APISettings) -> KafkaOutboxConsumer:
    target = settings.required_outbox_projection_target
    return KafkaOutboxConsumer(
        bootstrap_servers=settings.required_kafka_bootstrap_servers,
        topic=settings.kafka_outbox_topic,
        group_id=settings.outbox_consumer_group_for_projection(target),
    )


def _dead_letter_producer(settings: APISettings) -> KafkaDeadLetterProducer:
    return KafkaDeadLetterProducer(
        bootstrap_servers=settings.required_kafka_bootstrap_servers,
    )


def _projection_target_value(settings: APISettings) -> str:
    return settings.required_outbox_projection_target.value


def _ai_providers_for_target(settings: APISettings) -> AIProviders | None:
    if settings.required_outbox_projection_target in {
        OutboxProjectionTarget.QDRANT_DOCUMENT_CHUNKS,
        OutboxProjectionTarget.QDRANT_DOCUMENTS,
        OutboxProjectionTarget.QDRANT_SIGNALS,
        OutboxProjectionTarget.QDRANT_FOLDERS,
    }:
        return _build_ai_providers(settings)
    return None


def _projection_storage(settings: APISettings) -> OutboxProjectionStorage:
    target = settings.required_outbox_projection_target
    postgres = _postgres_client(settings)
    source_freshness = _source_freshness(postgres)
    projection_ledger = (
        None
        if target is OutboxProjectionTarget.NEO4J_GRAPH
        else _projection_ledger(postgres)
    )
    if target is OutboxProjectionTarget.QDRANT_DOCUMENT_CHUNKS:
        return OutboxProjectionStorage(
            chunk_vectors=_build_qdrant_document_chunk_vector_store(settings),
            projection_ledger=projection_ledger,
            source_freshness=source_freshness,
        )
    if target is OutboxProjectionTarget.QDRANT_DOCUMENTS:
        return OutboxProjectionStorage(
            document_vectors=_build_qdrant_document_vector_store(settings),
            projection_ledger=projection_ledger,
            source_freshness=source_freshness,
        )
    if target is OutboxProjectionTarget.QDRANT_SIGNALS:
        return OutboxProjectionStorage(
            signal_vectors=_build_qdrant_signal_vector_store(settings),
            projection_ledger=projection_ledger,
            source_freshness=source_freshness,
        )
    if target is OutboxProjectionTarget.QDRANT_FOLDERS:
        return OutboxProjectionStorage(
            folder_vectors=_build_qdrant_folder_vector_store(settings),
            projection_ledger=projection_ledger,
            source_freshness=source_freshness,
        )
    if target is OutboxProjectionTarget.NEO4J_GRAPH:
        return OutboxProjectionStorage(
            graph=_build_neo4j_store(settings),
            source_freshness=source_freshness,
        )
    raise RuntimeError(f"Unsupported FOLDMIND_OUTBOX_PROJECTION_TARGET: {target}")


def _projection_ledger(postgres: PostgresClient) -> TracedTransactionProvider:
    return TracedTransactionProvider(
        wrapped=PostgresProjectionLedgerSessionProvider(sessions=postgres),
        span_name="postgres.transaction.projection_ledger",
    )


def _source_freshness(postgres: PostgresClient) -> PostgresSourceFreshnessChecker:
    return PostgresSourceFreshnessChecker(sessions=postgres)


def _postgres_client(settings: APISettings) -> PostgresClient:
    return PostgresClient(
        settings=PostgresSettings(dsn=settings.required_postgres_dsn),
    )


def _outbox_shutdown_callbacks(
    *,
    storage_provider: Callable[[], OutboxProjectionStorage],
) -> tuple[ShutdownCallback, ...]:
    async def close_storage_resources() -> None:
        if getattr(storage_provider, "__IS_PROVIDER__", False):
            return
        initialized = getattr(storage_provider, "initialized", None)
        if initialized is not None:
            with suppress(Exception):
                is_initialized = initialized() if callable(initialized) else initialized
                if not is_initialized:
                    return
        storage = storage_provider()
        for callback in shutdown_callbacks_for(
            storage.chunk_vectors,
            storage.document_vectors,
            storage.signal_vectors,
            storage.folder_vectors,
            storage.graph,
            storage.projection_ledger,
            storage.source_freshness,
        ):
            await callback()

    return (close_storage_resources,)


class OutboxWorkerContainer(containers.DeclarativeContainer):  # type: ignore[misc]
    settings = providers.Singleton(APISettings)
    kafka_consumer = providers.Singleton(_kafka_consumer, settings=settings)
    dead_letter_producer = providers.Singleton(_dead_letter_producer, settings=settings)
    storage = providers.Singleton(_projection_storage, settings=settings)
    ai = providers.Singleton(_ai_providers_for_target, settings=settings)
    dispatcher = providers.Callable(
        _build_outbox_dispatcher,
        ai=ai,
        storage=storage,
        settings=settings,
        target=settings.provided.required_outbox_projection_target,
    )
    traced_dispatcher = providers.Factory(
        TracedOutboxConsumer,
        wrapped=dispatcher,
        span_name="outbox",
    )
    message_consumer = providers.Factory(
        OutboxProjectionMessageConsumer,
        dispatcher=traced_dispatcher,
        dead_letter_producer=dead_letter_producer,
        dead_letter_topic=settings.provided.kafka_dead_letter_topic,
        projection_target=providers.Callable(_projection_target_value, settings=settings),
        retry_policy=providers.Factory(
            RetryPolicy,
            max_retries=settings.provided.kafka_max_retries,
            backoff_seconds=settings.provided.kafka_retry_backoff_seconds,
        ),
    )
    runtime = providers.Factory(
        OutboxWorkerRuntime,
        consumer=kafka_consumer,
        message_consumer=message_consumer,
        shutdown_callbacks=providers.Callable(
            _outbox_shutdown_callbacks,
            storage_provider=providers.Object(storage),
        ),
    )
