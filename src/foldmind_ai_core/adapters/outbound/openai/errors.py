from __future__ import annotations

from foldmind_ai_core.core.application.errors import ProviderCallError


class AIProviderError(ProviderCallError):
    """Raised when an AI provider returns an invalid or failed response."""
