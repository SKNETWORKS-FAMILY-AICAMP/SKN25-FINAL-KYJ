from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from opentelemetry import trace

tracer = trace.get_tracer("foldmind_ai_core")


@dataclass(slots=True)
class TracedApplicationService:
    wrapped: Any
    service_name: str

    def __getattr__(self, name: str) -> Any:
        attribute = getattr(self.wrapped, name)
        if not callable(attribute):
            return attribute

        async def traced_method(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(
                f"application.{self.service_name}.{name}"
            ):
                return await attribute(*args, **kwargs)

        return traced_method


@dataclass(slots=True)
class _TracedWrapper:
    wrapped: Any
    span_name: str

    def close(self) -> Any:
        close = getattr(self.wrapped, "close", None)
        if close is None:
            return None
        return close()


class TracedOutboxConsumer(_TracedWrapper):
    __slots__ = ()

    async def consume_outbox_event(self, event: Any) -> None:
        event_type = getattr(event, "event_type", "unknown")
        with tracer.start_as_current_span(f"{self.span_name}.{event_type}"):
            await self.wrapped.consume_outbox_event(event)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.wrapped, name)


class TracedTransactionProvider(_TracedWrapper):
    __slots__ = ()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Any]:
        with tracer.start_as_current_span(self.span_name):
            async with self.wrapped.transaction() as session:
                yield session


class TracedSessionProvider(_TracedWrapper):
    __slots__ = ()

    @asynccontextmanager
    async def session(self) -> AsyncIterator[Any]:
        with tracer.start_as_current_span(self.span_name):
            async with self.wrapped.session() as session:
                yield session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Any]:
        with tracer.start_as_current_span(f"{self.span_name}.transaction"):
            async with self.wrapped.transaction() as session:
                yield session
