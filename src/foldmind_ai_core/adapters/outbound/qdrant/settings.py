from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.shared.validation import require_non_blank


@dataclass(frozen=True, slots=True)
class QdrantSettings:
    url: str | None = None
    api_key: str | None = None

    def __post_init__(self) -> None:
        if self.url is not None:
            object.__setattr__(self, "url", require_non_blank(self.url, "url"))
        if self.api_key is not None:
            object.__setattr__(
                self,
                "api_key",
                require_non_blank(self.api_key, "api_key"),
            )
