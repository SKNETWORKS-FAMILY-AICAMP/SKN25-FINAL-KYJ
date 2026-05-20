from __future__ import annotations

import json
from collections.abc import Sequence
from enum import StrEnum
from typing import Annotated, Any, cast

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _clean_origins(values: Sequence[object]) -> tuple[str, ...]:
    origins: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise TypeError("cors_origins entries must be strings.")
        if stripped := value.strip():
            origins.append(stripped)
    return tuple(origins)


def _parse_cors_origins(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ()
        if stripped.startswith("["):
            parsed = json.loads(stripped)
            if not isinstance(parsed, list):
                raise TypeError("cors_origins JSON value must be a list of strings.")
            return _clean_origins(parsed)
        return _clean_origins(stripped.split(","))

    if isinstance(value, Sequence):
        return _clean_origins(value)

    raise TypeError("cors_origins must be a string or sequence of strings.")


def _required_text(value: str | None, message: str) -> str:
    if value is None or not value.strip():
        raise ValueError(message)
    return value.strip()


def _required_secret(value: SecretStr | None, message: str) -> str:
    if value is None:
        raise ValueError(message)
    secret = value.get_secret_value()
    if not secret.strip():
        raise ValueError(message)
    return secret


_OPTIONAL_SETTING_FIELDS = (
    "openai_api_key",
    "openai_base_url",
    "prompt_root",
    "document_profile_prompt_version",
    "workflow_checkpoint_dsn",
    "postgres_dsn",
    "qdrant_url",
    "qdrant_api_key",
    "neo4j_uri",
    "neo4j_user",
    "neo4j_password",
    "neo4j_database",
    "embedding_model",
    "embedding_version",
    "chunking_version",
    "index_schema_version",
    "kafka_bootstrap_servers",
)


class AIProvider(StrEnum):
    OPENAI = "openai"


class OutboxProjectionTarget(StrEnum):
    QDRANT_DOCUMENT_CHUNKS = "qdrant-document-chunks"
    QDRANT_DOCUMENTS = "qdrant-documents"
    QDRANT_SIGNALS = "qdrant-signals"
    QDRANT_FOLDERS = "qdrant-folders"
    NEO4J_GRAPH = "neo4j-graph"


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="FOLDMIND_",
        extra="ignore",
        populate_by_name=True,
    )

    title: str = Field(default="FoldMind AI Core", validation_alias="FOLDMIND_API_TITLE")
    version: str = Field(default="0.1.0", validation_alias="FOLDMIND_API_VERSION")
    cors_origins: Annotated[tuple[str, ...], NoDecode] = Field(
        default_factory=tuple,
        validation_alias="FOLDMIND_CORS_ORIGINS",
    )
    cors_allow_credentials: bool = Field(
        default=True,
        validation_alias="FOLDMIND_CORS_ALLOW_CREDENTIALS",
    )
    ai_provider: AIProvider = Field(
        default=AIProvider.OPENAI,
    )
    openai_api_key: SecretStr | None = Field(
        default=None,
    )
    openai_base_url: str | None = Field(
        default=None,
    )
    openai_timeout_seconds: float = Field(
        default=60.0,
        gt=0,
    )
    openai_max_retries: int = Field(
        default=2,
        ge=0,
    )
    llm_model: str = Field(
        default="gpt-4.1-mini",
    )
    prompt_root: str | None = Field(
        default=None,
    )
    document_profile_prompt_version: str | None = Field(
        default=None,
    )
    workflow_checkpoint_dsn: str | None = Field(
        default=None,
        validation_alias="FOLDMIND_WORKFLOW_CHECKPOINT_DSN",
    )
    allow_in_memory_workflow_checkpoint: bool = Field(
        default=False,
        validation_alias="FOLDMIND_ALLOW_IN_MEMORY_WORKFLOW_CHECKPOINT",
    )
    postgres_dsn: str | None = Field(
        default=None,
    )
    qdrant_url: str | None = Field(
        default=None,
    )
    qdrant_api_key: SecretStr | None = Field(
        default=None,
    )
    qdrant_document_chunk_collection: str = Field(
        default="document_chunks",
    )
    qdrant_document_collection: str = Field(
        default="documents",
    )
    qdrant_folder_collection: str = Field(
        default="folders",
    )
    qdrant_signal_collection: str = Field(
        default="signals",
    )
    qdrant_vector_size: int = Field(
        default=1536,
    )
    qdrant_distance: str = Field(
        default="Cosine",
    )
    neo4j_uri: str | None = Field(
        default=None,
    )
    neo4j_user: str | None = Field(
        default=None,
    )
    neo4j_password: SecretStr | None = Field(
        default=None,
    )
    neo4j_database: str | None = Field(
        default=None,
    )
    validate_storage_on_load: bool = Field(
        default=False,
    )
    embedding_model: str | None = Field(
        default=None,
    )
    embedding_version: str | None = Field(
        default=None,
    )
    chunking_version: str | None = Field(
        default=None,
    )
    index_schema_version: str | None = Field(
        default=None,
    )
    embedding_dimensions: int | None = Field(
        default=None,
        gt=0,
    )
    kafka_bootstrap_servers: str | None = Field(
        default=None,
    )
    kafka_outbox_topic: str = Field(
        default="indexing-events",
    )
    outbox_projection_target: OutboxProjectionTarget | None = Field(
        default=None,
    )
    kafka_dead_letter_topic: str = Field(
        default="indexing-events.dlq",
    )
    kafka_max_retries: int = Field(
        default=3,
        ge=0,
    )
    kafka_retry_backoff_seconds: float = Field(
        default=1.0,
        ge=0.0,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> tuple[str, ...]:
        return _parse_cors_origins(value)

    @field_validator(*_OPTIONAL_SETTING_FIELDS, mode="before")
    @classmethod
    def blank_optional_settings_become_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def qdrant_api_key_value(self) -> str | None:
        if self.qdrant_api_key is None:
            return None
        return self.qdrant_api_key.get_secret_value()

    @property
    def openai_api_key_value(self) -> str | None:
        if self.openai_api_key is None:
            return None
        return self.openai_api_key.get_secret_value()

    @property
    def neo4j_password_value(self) -> str | None:
        if self.neo4j_password is None:
            return None
        return self.neo4j_password.get_secret_value()

    @property
    def required_openai_api_key(self) -> str:
        return _required_secret(
            self.openai_api_key,
            "FOLDMIND_OPENAI_API_KEY is required when FOLDMIND_AI_PROVIDER=openai.",
        )

    @property
    def required_embedding_model(self) -> str:
        return _required_text(
            self.embedding_model,
            "FOLDMIND_EMBEDDING_MODEL is required for embeddings.",
        )

    @property
    def required_document_profile_prompt_version(self) -> str:
        return _required_text(
            self.document_profile_prompt_version,
            "FOLDMIND_DOCUMENT_PROFILE_PROMPT_VERSION is required for document profiling.",
        )

    @property
    def required_postgres_dsn(self) -> str:
        return _required_text(
            self.postgres_dsn,
            "FOLDMIND_POSTGRES_DSN is required for the standard AI-Core API.",
        )

    @property
    def required_qdrant_url(self) -> str:
        return _required_text(
            self.qdrant_url,
            "FOLDMIND_QDRANT_URL is required for the standard AI-Core API.",
        )

    @property
    def required_neo4j_uri(self) -> str:
        return _required_text(
            self.neo4j_uri,
            "FOLDMIND_NEO4J_URI, FOLDMIND_NEO4J_USER, "
            "and FOLDMIND_NEO4J_PASSWORD are required.",
        )

    @property
    def required_embedding_version(self) -> str:
        return _required_text(
            self.embedding_version,
            "FOLDMIND_EMBEDDING_VERSION is required for indexing.",
        )

    @property
    def required_chunking_version(self) -> str:
        return _required_text(
            self.chunking_version,
            "FOLDMIND_CHUNKING_VERSION is required for indexing.",
        )

    @property
    def required_index_schema_version(self) -> str:
        return _required_text(
            self.index_schema_version,
            "FOLDMIND_INDEX_SCHEMA_VERSION is required for indexing.",
        )

    @property
    def qdrant_collection_vector_size(self) -> int:
        return self.embedding_dimensions or self.qdrant_vector_size

    @property
    def required_kafka_bootstrap_servers(self) -> str:
        return _required_text(
            self.kafka_bootstrap_servers,
            "FOLDMIND_KAFKA_BOOTSTRAP_SERVERS is required for the outbox worker.",
        )

    @property
    def required_outbox_projection_target(self) -> OutboxProjectionTarget:
        if self.outbox_projection_target is None:
            raise ValueError(
                "FOLDMIND_OUTBOX_PROJECTION_TARGET is required for the outbox worker."
            )
        return self.outbox_projection_target

    def outbox_consumer_group_for_projection(
        self,
        target: OutboxProjectionTarget,
    ) -> str:
        return f"foldmind-ai-core-outbox-{target.value}"

    @property
    def required_neo4j_user(self) -> str:
        return _required_text(
            self.neo4j_user,
            "FOLDMIND_NEO4J_URI, FOLDMIND_NEO4J_USER, "
            "and FOLDMIND_NEO4J_PASSWORD are required.",
        )

    @property
    def required_neo4j_password(self) -> str:
        return _required_secret(
            self.neo4j_password,
            "FOLDMIND_NEO4J_URI, FOLDMIND_NEO4J_USER, "
            "and FOLDMIND_NEO4J_PASSWORD are required.",
        )

    @model_validator(mode="after")
    def validate_storage_when_requested(self) -> APISettings:
        if (
            self.embedding_dimensions is not None
            and "qdrant_vector_size" in self.model_fields_set
            and self.qdrant_vector_size != self.embedding_dimensions
        ):
            raise ValueError(
                "FOLDMIND_QDRANT_VECTOR_SIZE must match "
                "FOLDMIND_EMBEDDING_DIMENSIONS when both are set."
            )
        if self.validate_storage_on_load:
            self.require_configured_storage()
        return self

    def require_configured_storage(self) -> None:
        _ = self.required_qdrant_url
        _ = self.required_postgres_dsn
        _ = self.required_neo4j_uri
        _ = self.required_neo4j_user
        _ = self.required_neo4j_password


def load_settings(env_file: str | None = None) -> APISettings:
    if env_file is not None:
        settings_class: Any = APISettings
        return cast(APISettings, settings_class(_env_file=env_file))
    return APISettings()
