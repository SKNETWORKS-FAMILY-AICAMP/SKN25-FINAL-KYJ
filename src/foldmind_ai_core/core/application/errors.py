from __future__ import annotations


class ApplicationServiceError(RuntimeError):
    """Expected application service failure."""


class ResourceNotFoundError(ApplicationServiceError):
    """Raised when a requested application resource cannot be found."""


class NoCandidatesError(ResourceNotFoundError):
    """Raised when an application service needs at least one candidate but none exist."""


class ConcurrentTaskUpdateError(ApplicationServiceError):
    """Raised when a workflow task changed while a long-running operation was active."""


class InvalidAgentOutputError(ApplicationServiceError):
    """Raised when an agent returns output that does not match its contract."""


class ProviderContractError(ApplicationServiceError):
    """Raised when an outbound provider violates its application port contract."""


class InfrastructureError(RuntimeError):
    """Unexpected failure in an outbound adapter or infrastructure dependency."""


class DatabaseError(InfrastructureError):
    """Raised when a database adapter fails unexpectedly."""


class ProviderCallError(InfrastructureError):
    """Raised when an external provider call fails unexpectedly."""
