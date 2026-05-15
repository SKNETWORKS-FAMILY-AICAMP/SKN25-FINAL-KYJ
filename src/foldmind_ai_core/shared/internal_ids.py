from __future__ import annotations

import uuid


def new_internal_id() -> str:
    return str(uuid.uuid4())


def stable_internal_id(*parts: object) -> str:
    value = ":".join(str(part) for part in parts)
    return str(uuid.uuid5(uuid.NAMESPACE_URL, value))
