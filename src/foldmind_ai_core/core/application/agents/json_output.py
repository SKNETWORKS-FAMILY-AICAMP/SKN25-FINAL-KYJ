from __future__ import annotations

import json
from typing import cast

from foldmind_ai_core.shared.types import JsonObject


def parse_json_object_output(raw: str) -> JsonObject:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Agent response did not contain a JSON object.")
    value = json.loads(raw[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("Agent response JSON must be an object.")
    return cast(JsonObject, value)
