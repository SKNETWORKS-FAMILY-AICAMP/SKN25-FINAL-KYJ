from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from foldmind_ai_core.shared.validation import InvalidInputError, require_non_blank


@dataclass(frozen=True, slots=True)
class FilePromptRepository:
    root: Path

    def get(self, name: str) -> str:
        require_non_blank(name, "name")
        path = self.root / f"{name}.md"
        if not path.is_file():
            raise InvalidInputError(f"Prompt not found: {name}")
        return path.read_text(encoding="utf-8")
