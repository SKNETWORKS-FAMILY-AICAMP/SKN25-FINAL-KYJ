from __future__ import annotations

from foldmind_ai_core.shared.validation import require_non_blank


def require_source_version(value: str, name: str) -> str:
    return require_non_blank(value, name)
