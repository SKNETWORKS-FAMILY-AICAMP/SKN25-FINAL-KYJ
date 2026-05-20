from __future__ import annotations


class UseCaseError(RuntimeError):
    """Expected application use-case failure."""


class ResourceNotFoundError(UseCaseError):
    """Raised when a requested application resource cannot be found."""


class NoCandidatesError(ResourceNotFoundError):
    """Raised when a use case needs at least one candidate but none exist."""


class InvalidAgentOutputError(UseCaseError):
    """Raised when an agent returns output that does not match its contract."""


class ProviderContractError(UseCaseError):
    """Raised when an outbound provider violates its application port contract."""
