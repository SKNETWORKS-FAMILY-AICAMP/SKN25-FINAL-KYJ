from __future__ import annotations

import json
from collections.abc import Sequence
from enum import StrEnum
from typing import Annotated, Any

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _split_csv(value: str) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


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
        return _split_csv(stripped)

    if isinstance(value, Sequence):
        return _clean_origins(value)

    raise TypeError("cors_origins must be a string or sequence of strings.")


class AIProvider(StrEnum):
    OPENAI = "openai"


class OutboxProjectionTarget(StrEnum):
    QDRANT_DOCUMENT_CHUNKS = "qdrant-document-chunks"
    QDRANT_DOCUMENTS = "qdrant-documents"
    QDRANT_FOLDERS = "qdrant-folders"
    NEO4J_GRAPH = "neo4j-graph"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
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
        validation_alias=AliasChoices("AI_PROVIDER", "FOLDMIND_AI_PROVIDER"),
    )
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "FOLDMIND_OPENAI_API_KEY"),
    )
    openai_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_BASE_URL", "FOLDMIND_OPENAI_BASE_URL"),
    )
    openai_timeout_seconds: float = Field(
        default=60.0,
        gt=0,
        validation_alias=AliasChoices(
            "OPENAI_TIMEOUT_SECONDS",
            "FOLDMIND_OPENAI_TIMEOUT_SECONDS",
        ),
    )
    openai_max_retries: int = Field(
        default=2,
        ge=0,
        validation_alias=AliasChoices("OPENAI_MAX_RETRIES", "FOLDMIND_OPENAI_MAX_RETRIES"),
    )
    llm_model: str = Field(
        default="gpt-4.1-mini",
        validation_alias=AliasChoices(
            "LLM_MODEL",
            "FOLDMIND_LLM_MODEL",
        ),
    )
    prompt_root: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PROMPT_ROOT", "FOLDMIND_PROMPT_ROOT"),
    )
    profile_version: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PROFILE_VERSION", "FOLDMIND_PROFILE_VERSION"),
    )
    profile_schema_version: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "PROFILE_SCHEMA_VERSION",
            "FOLDMIND_PROFILE_SCHEMA_VERSION",
        ),
    )
    document_profile_prompt_version: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DOCUMENT_PROFILE_PROMPT_VERSION",
            "FOLDMIND_DOCUMENT_PROFILE_PROMPT_VERSION",
        ),
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
        validation_alias=AliasChoices("POSTGRES_DSN", "FOLDMIND_POSTGRES_DSN"),
    )
    qdrant_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("QDRANT_URL", "FOLDMIND_QDRANT_URL"),
    )
    qdrant_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("QDRANT_API_KEY", "FOLDMIND_QDRANT_API_KEY"),
    )
    qdrant_document_chunk_collection: str = Field(
        default="document_chunks",
        validation_alias=AliasChoices(
            "QDRANT_DOCUMENT_CHUNK_COLLECTION",
            "FOLDMIND_QDRANT_DOCUMENT_CHUNK_COLLECTION",
        ),
    )
    qdrant_document_collection: str = Field(
        default="documents",
        validation_alias=AliasChoices(
            "QDRANT_DOCUMENT_COLLECTION",
            "FOLDMIND_QDRANT_DOCUMENT_COLLECTION",
        ),
    )
    qdrant_folder_collection: str = Field(
        default="folders",
        validation_alias=AliasChoices(
            "QDRANT_FOLDER_COLLECTION",
            "FOLDMIND_QDRANT_FOLDER_COLLECTION",
        ),
    )
    qdrant_vector_size: int = Field(
        default=1536,
        validation_alias=AliasChoices("QDRANT_VECTOR_SIZE", "FOLDMIND_QDRANT_VECTOR_SIZE"),
    )
    qdrant_distance: str = Field(
        default="Cosine",
        validation_alias=AliasChoices("QDRANT_DISTANCE", "FOLDMIND_QDRANT_DISTANCE"),
    )
    neo4j_uri: str | None = Field(
        default=None,
        validation_alias=AliasChoices("NEO4J_URI", "FOLDMIND_NEO4J_URI"),
    )
    neo4j_user: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "NEO4J_USER",
            "NEO4J_USERNAME",
            "FOLDMIND_NEO4J_USERNAME",
        ),
    )
    neo4j_password: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("NEO4J_PASSWORD", "FOLDMIND_NEO4J_PASSWORD"),
    )
    neo4j_database: str | None = Field(
        default=None,
        validation_alias=AliasChoices("NEO4J_DATABASE", "FOLDMIND_NEO4J_DATABASE"),
    )
    validate_storage_on_load: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "VALIDATE_STORAGE_ON_LOAD",
            "FOLDMIND_VALIDATE_STORAGE_ON_LOAD",
        ),
    )
    embedding_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EMBEDDING_MODEL", "FOLDMIND_EMBEDDING_MODEL"),
    )
    embedding_version: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "EMBEDDING_VERSION",
            "FOLDMIND_EMBEDDING_VERSION",
        ),
    )
    chunking_version: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "CHUNKING_VERSION",
            "FOLDMIND_CHUNKING_VERSION",
        ),
    )
    index_schema_version: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "INDEX_SCHEMA_VERSION",
            "FOLDMIND_INDEX_SCHEMA_VERSION",
        ),
    )
    embedding_dimensions: int | None = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices(
            "EMBEDDING_DIMENSIONS",
            "FOLDMIND_EMBEDDING_DIMENSIONS",
        ),
    )
    kafka_bootstrap_servers: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "KAFKA_BOOTSTRAP_SERVERS",
            "FOLDMIND_KAFKA_BOOTSTRAP_SERVERS",
        ),
    )
    kafka_outbox_topic: str = Field(
        default="indexing-events",
        validation_alias=AliasChoices(
            "KAFKA_OUTBOX_TOPIC",
            "FOLDMIND_KAFKA_OUTBOX_TOPIC",
        ),
    )
    outbox_projection_target: OutboxProjectionTarget | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "OUTBOX_PROJECTION_TARGET",
            "FOLDMIND_OUTBOX_PROJECTION_TARGET",
        ),
    )
    kafka_dlq_topic: str = Field(
        default="indexing-events.dlq",
        validation_alias=AliasChoices(
            "KAFKA_DLQ_TOPIC",
            "FOLDMIND_KAFKA_DLQ_TOPIC",
        ),
    )
    kafka_max_retries: int = Field(
        default=3,
        ge=0,
        validation_alias=AliasChoices(
            "KAFKA_MAX_RETRIES",
            "FOLDMIND_KAFKA_MAX_RETRIES",
        ),
    )
    kafka_retry_backoff_seconds: float = Field(
        default=1.0,
        ge=0.0,
        validation_alias=AliasChoices(
            "KAFKA_RETRY_BACKOFF_SECONDS",
            "FOLDMIND_KAFKA_RETRY_BACKOFF_SECONDS",
        ),
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> tuple[str, ...]:
        return _parse_cors_origins(value)

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
        if self.openai_api_key is None:
            raise ValueError("OPENAI_API_KEY is required when AI_PROVIDER=openai.")
        return self.openai_api_key.get_secret_value()

    @property
    def required_embedding_model(self) -> str:
        if not self.embedding_model:
            raise ValueError("EMBEDDING_MODEL is required for embeddings.")
        return self.embedding_model

    @property
    def required_profile_version(self) -> str:
        if not self.profile_version:
            raise ValueError("PROFILE_VERSION is required for document profiling.")
        return self.profile_version

    @property
    def required_profile_schema_version(self) -> str:
        if not self.profile_schema_version:
            raise ValueError("PROFILE_SCHEMA_VERSION is required for document profiling.")
        return self.profile_schema_version

    @property
    def required_document_profile_prompt_version(self) -> str:
        if not self.document_profile_prompt_version:
            raise ValueError(
                "DOCUMENT_PROFILE_PROMPT_VERSION is required for document profiling."
            )
        return self.document_profile_prompt_version

    @property
    def required_postgres_dsn(self) -> str:
        if not self.postgres_dsn:
            raise ValueError("POSTGRES_DSN is required for the standard AI-Core API.")
        return self.postgres_dsn

    @property
    def required_qdrant_url(self) -> str:
        if not self.qdrant_url:
            raise ValueError("QDRANT_URL is required for the standard AI-Core API.")
        return self.qdrant_url

    @property
    def required_neo4j_uri(self) -> str:
        if not self.neo4j_uri:
            raise ValueError("NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD are required.")
        return self.neo4j_uri

    @property
    def required_embedding_version(self) -> str:
        if not self.embedding_version:
            raise ValueError("EMBEDDING_VERSION is required for indexing.")
        return self.embedding_version

    @property
    def required_chunking_version(self) -> str:
        if not self.chunking_version:
            raise ValueError("CHUNKING_VERSION is required for indexing.")
        return self.chunking_version

    @property
    def required_index_schema_version(self) -> str:
        if not self.index_schema_version:
            raise ValueError("INDEX_SCHEMA_VERSION is required for indexing.")
        return self.index_schema_version

    @property
    def required_kafka_bootstrap_servers(self) -> str:
        if not self.kafka_bootstrap_servers:
            raise ValueError("KAFKA_BOOTSTRAP_SERVERS is required for the outbox worker.")
        return self.kafka_bootstrap_servers

    @property
    def required_outbox_projection_target(self) -> OutboxProjectionTarget:
        if self.outbox_projection_target is None:
            raise ValueError("OUTBOX_PROJECTION_TARGET is required for the outbox worker.")
        return self.outbox_projection_target

    def outbox_consumer_group_for_projection(
        self,
        target: OutboxProjectionTarget,
    ) -> str:
        return f"foldmind-ai-core-outbox-{target.value}"

    @property
    def required_neo4j_user(self) -> str:
        if not self.neo4j_user:
            raise ValueError("NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD are required.")
        return self.neo4j_user

    @property
    def required_neo4j_password(self) -> str:
        if self.neo4j_password is None:
            raise ValueError("NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD are required.")
        return self.neo4j_password.get_secret_value()

    @model_validator(mode="after")
    def validate_storage_when_requested(self) -> Settings:
        if self.validate_storage_on_load:
            self.require_configured_storage()
        return self

    def require_configured_storage(self) -> None:
        if not self.qdrant_url:
            raise ValueError("QDRANT_URL is required for the standard AI-Core API.")
        if not self.postgres_dsn:
            raise ValueError("POSTGRES_DSN is required for the standard AI-Core API.")
        if not self.neo4j_uri or not self.neo4j_user or not self.neo4j_password:
            raise ValueError(
                "NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD are required "
                "for the standard AI-Core API."
            )


APISettings = Settings


def load_settings(env_file: str | None = None) -> Settings:
    if env_file is not None:
        return Settings(_env_file=env_file)  # type: ignore[call-arg]
    return Settings()
