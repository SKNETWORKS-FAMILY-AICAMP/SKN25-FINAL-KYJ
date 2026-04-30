from __future__ import annotations

import os
from dataclasses import dataclass, field


def _split_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _read_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


@dataclass(slots=True)
class APISettings:
    title: str = "FoldMind AI Core"
    version: str = "0.1.0"
    cors_origins: tuple[str, ...] = field(default_factory=tuple)
    cors_allow_credentials: bool = True

    @classmethod
    def from_env(cls) -> APISettings:
        return cls(
            title=os.getenv("FOLDMIND_API_TITLE", "FoldMind AI Core"),
            version=os.getenv("FOLDMIND_API_VERSION", "0.1.0"),
            cors_origins=_split_csv(os.getenv("FOLDMIND_CORS_ORIGINS")),
            cors_allow_credentials=_read_bool(
                os.getenv("FOLDMIND_CORS_ALLOW_CREDENTIALS"),
                default=True,
            ),
        )
