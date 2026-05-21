from __future__ import annotations

from collections.abc import Mapping

from foldmind_ai_core.shared.canonical_json import json_digest


def input_digest(kind: str, payload: Mapping[str, object]) -> str:
    return json_digest(
        {
            "kind": kind,
            "payload": dict(payload),
        }
    )
