from __future__ import annotations

import hashlib
import json

from foldmind_ai_core.shared.types import JsonObject


def canonical_json(value: JsonObject) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def json_digest(value: JsonObject) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
