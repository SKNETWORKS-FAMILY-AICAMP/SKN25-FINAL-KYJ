from __future__ import annotations


class UseCaseError(RuntimeError):
    """Base class for expected application use-case failures."""


class ResourceNotFoundError(UseCaseError):
    """Raised when a requested application resource cannot be found."""


class NoCandidatesError(ResourceNotFoundError):
    """Raised when a use case needs at least one candidate but none exist."""
