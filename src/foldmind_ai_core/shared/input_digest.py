from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from foldmind_ai_core.shared.canonical_json import json_digest
from foldmind_ai_core.shared.types import JsonObject


def input_digest(kind: str, payload: Mapping[str, object]) -> str:
    return json_digest(
        {
            "kind": kind,
            "payload": cast(JsonObject, dict(payload)),
        }
    )
