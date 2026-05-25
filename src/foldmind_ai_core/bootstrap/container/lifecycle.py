from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

logger = logging.getLogger(__name__)

ShutdownCallback = Callable[[], Awaitable[None]]


def shutdown_callbacks_for(*resources: Any) -> tuple[ShutdownCallback, ...]:
    return tuple(_shutdown_callback(resource) for resource in resources if resource is not None)


def lazy_shutdown_callbacks_for(
    *resource_factories: Callable[[], Any],
) -> tuple[ShutdownCallback, ...]:
    resolved_resources = tuple(_resolved_resource(factory) for factory in resource_factories)
    return shutdown_callbacks_for(*resolved_resources)


def _shutdown_callback(resource: Any) -> ShutdownCallback:
    async def shutdown() -> None:
        await close_resource(resource)

    return shutdown


def _resolved_resource(resource_factory: Callable[[], Any]) -> Any | None:
    if getattr(resource_factory, "__IS_PROVIDER__", False):
        return None
    initialized = getattr(resource_factory, "initialized", None)
    if initialized is not None:
        with suppress(Exception):
            is_initialized = initialized() if callable(initialized) else initialized
            if not is_initialized:
                return None
    try:
        return resource_factory()
    except Exception:
        logger.exception("Failed to resolve shutdown resource.")
        return None


async def close_resource(resource: Any) -> None:
    target = resource
    visited: set[int] = set()
    while target is not None and id(target) not in visited:
        visited.add(id(target))
        close = getattr(target, "close", None)
        if close is not None:
            try:
                result = close()
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Failed to close resource.", extra={"resource": repr(target)})
            return
        target = getattr(target, "client", None)
