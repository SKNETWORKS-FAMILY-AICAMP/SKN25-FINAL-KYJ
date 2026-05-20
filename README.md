# FoldMind-AI-Core

[한국어 README](README.ko.md)

FoldMind-AI-Core is the AI processing server that runs beside the FoldMind app
server. The app server remains the owner of source documents, folders,
permissions, users, and business rules. AI-Core receives current-state snapshots
from the app server and stores only derived AI data: search payloads, document
AI profiles, lightweight folder metadata indexes, graph relationships, workflow
snapshots, and task events.

AI-Core does not replace the app server database. It does not store or mutate
canonical source data.

## At A Glance

| Area | What Happens |
| --- | --- |
| Document indexing | Split document text into chunks, embed each chunk, create a document AI profile, and store graph DB relationships. |
| Folder indexing | Embed folder metadata and store lightweight folder vector and graph hierarchy records. |
| Document search | Convert the question into an embedding, then use the vector DB and graph DB together to find evidence chunks. |
| Answer generation | Send retrieved chunks to the LLM and return generated text with citations. |
| Workflow tasks | Break a natural-language request into steps, execute AI work, and return source-data changes as host actions for the app server. |
| Persistence scope | Store document profiles, vector payloads, graph relationships, task snapshots, and task events. Do not store canonical source data. |

## Responsibility Boundary

| Owner | Owns |
| --- | --- |
| FoldMind app server | Source documents, source folders, source tags, permissions, users, and business rules. |
| AI-Core | Document AI profiles, vector index payloads, graph DB relationships, retrieval results, generated outputs, workflow state, and proposed host actions. |

AI-Core does not call the app server directly. When a task needs to create a folder,
move a document, or perform another source-data change, AI-Core returns a
`HostAction`. The app server approves, executes, rejects, or modifies that action
and reports the result back to AI-Core.

## Main Capabilities

**Document Indexing**

The app server sends a `SourceDocument` snapshot. AI-Core splits the body into
searchable `DocumentChunk` records and creates an embedding for each chunk. The LLM
then creates a profiling manifest (`DocumentProfile`) and extracted
`KnowledgeSignal` records for summary, concept, entity, issue, commitment, and
claim evidence.

Indexing writes the profile and an outbox event atomically to PostgreSQL.
Debezium Kafka consumers asynchronously project Qdrant and graph DB state. Outbox
events carry a database-generated sequence, idempotency key, and `AGGREGATE:ID`
event key for stream ordering, idempotency, and dead-letter context. Qdrant
stores chunk, signal, folder, and document-level vectors. The graph DB stores
document-to-folder, document-to-signal, folder-to-signal, and folder hierarchy
relationships. Neo4j projection state is not mirrored in
PostgreSQL; recovery uses outbox replay plus Kafka dead-letter handling. Chunk
text stays in Qdrant; chunk nodes are not projected into the graph DB.

**Folder Indexing**

The app server sends a `SourceFolder` snapshot. AI-Core reads folder metadata and
stores it as a lightweight derived index. It embeds the folder name, path, and
description into the Qdrant folder collection and projects a `Folder` node plus
folder hierarchy edges into the graph DB.

Folder indexing does not create or store a PostgreSQL folder profile. Folder names,
paths, descriptions, and hierarchy records are rebuildable search indexes; the app
server remains canonical for folder display data and permissions.

**Document Search**

Document search uses two stores together.

1. Qdrant finds chunks and documents that are semantically close to the question.
2. The graph DB finds documents linked through folders and knowledge signals.
3. AI-Core combines the document IDs found by both stores and searches chunks inside those documents.
4. Retrieved chunks are ranked by score.
5. The relevance filter agent removes chunks that do not answer the question.

`/retrieval/search` returns the resulting chunk list.

**Question Answering**

`/retrieval/answer` first runs document search. It then formats the retrieved chunk
text, document ID, chunk ID, and score as context for the LLM. The LLM writes the
answer using that context as evidence. The response includes generated text and
citations for the chunks used as evidence.

**Recommendations**

`/retrieval/folder-recommendations` receives a document snapshot and returns the
folder ID that best matches that document, with a score and reason. The app server
uses the returned `folder_id` to enrich display fields and decide where to place a
document.

**Workflow Tasks**

`/tasks` receives a natural-language request. AI-Core turns the request into steps
such as search, recommendation, summary, answer generation, draft generation, idea
generation, or host-action planning. AI-Core executes AI-only steps itself. For
source-data changes, AI-Core returns a `HostAction` and waits for the app server to
report the result.

## Typical App-Server Flows

### 1. Index A Document

| Step | What Happens |
| --- | --- |
| App server sends | `POST /indexing/documents` with title, body, version, folder IDs, and metadata. |
| AI-Core validates | Tenant, source identity, version, and indexable text are checked. |
| AI-Core creates chunks | The body is split into `DocumentChunk` records. |
| AI-Core creates embeddings | Each chunk body is converted into a vector. |
| AI-Core creates signals | The LLM generates a profiling manifest plus summary, concept, entity, issue, commitment, and claim signals. |
| AI-Core stores derived data | PostgreSQL, Qdrant, and the graph DB receive derived records. |
| App server receives | The indexed chunk count. The source document remains owned by the app server. |

### 2. Answer A Question

| Step | What Happens |
| --- | --- |
| App server sends | `POST /retrieval/answer` with question, tenant, and search scope. |
| AI-Core finds document IDs | Qdrant document vectors and graph DB relationship search find related document IDs. |
| AI-Core finds chunks | Chunks are searched inside those documents. If no document IDs are found, chunk search runs directly within the requested scope. |
| AI-Core filters chunks | The relevance filter agent removes chunks unrelated to the question. |
| AI-Core generates an answer | The answer generation agent writes an answer from the remaining chunks. |
| App server receives | Answer text and citations for evidence chunks. |

### 3. Run A Workflow Task

| Step | What Happens |
| --- | --- |
| App server starts | `POST /tasks` with tenant and a natural-language request. AI-Core generates the task ID and task request ID. |
| App server continues | `POST /tasks` with the existing `task_id` appends another request to the same task. |
| AI-Core plans | The planning agent turns the request into executable workflow steps. |
| AI-Core executes | Search, recommendation, summary, answer, draft, and idea steps run inside AI-Core. |
| AI-Core proposes actions | Source-data changes are returned as `HostAction` values in the task snapshot. |
| App server handles actions | The app server approves, executes, rejects, modifies, skips, or retries each action. |
| App server reports | `POST /tasks/actions/result` sends the action result to AI-Core. |
| AI-Core resumes | The workflow resumes from the saved checkpoint and returns the latest task snapshot. |

## REST API

All REST DTOs reject unknown fields. Input validation errors return `422`. Missing
tasks or recommendation targets return `404` on routes that handle those cases.

### System

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check that the process is running. The normal response is `{"status": "ok"}`. |

### Indexing

| Method | Path | Request DTO | Response DTO | Purpose |
| --- | --- | --- | --- | --- |
| `POST` | `/indexing/documents` | `IndexDocumentRequest` | `IndexDocumentResponse` | Index a document snapshot and return the created chunk count. |
| `DELETE` | `/indexing/documents/{document_id}` | - | `204 No Content` | Delete the document profile, vector payloads, and graph DB relationships. |
| `POST` | `/indexing/folders` | `IndexFolderRequest` | `IndexFolderResponse` | Index a folder snapshot and return the searchable folder model. |
| `DELETE` | `/indexing/folders/{folder_id}` | - | `204 No Content` | Delete the folder vector payloads and graph DB relationships. |

### Retrieval And Recommendations

| Method | Path | Request DTO | Response DTO | Purpose |
| --- | --- | --- | --- | --- |
| `POST` | `/retrieval/search` | `SearchDocumentsRequest` | `SearchDocumentsResponse` | Return AI-Core-stored document chunks related to the question. |
| `POST` | `/retrieval/answer` | `AnswerQuestionRequest` | `GeneratedTextResponse` | Find related chunks, then generate an answer and citations from those chunks. |
| `POST` | `/retrieval/folder-recommendations` | `RecommendFolderRequest` | `RecommendFolderResponse` | Recommend the best `folder_id` for a document snapshot. |

### Workflow Tasks

| Method | Path | Request DTO | Response DTO | Purpose |
| --- | --- | --- | --- | --- |
| `POST` | `/tasks` | `CreateTaskRequest` | `TaskSnapshotResponse` | Start a task or append a request to an existing task. |
| `GET` | `/tasks/{task_id}` | - | `TaskSnapshotResponse` | Read the latest task snapshot visible to the app server. |
| `DELETE` | `/tasks/requests/{task_request_id}` | - | `TaskSnapshotResponse` | Mark a request entry as removed and replan from the active requests. |
| `POST` | `/tasks/actions/result` | `RecordHostActionResultRequest` | `RecordHostActionResultResponse` | Resume a paused workflow after the app server reports a host action result. |

## Search Behavior

Document search is implemented by `FindDocumentsUseCase`.

1. Convert the question text into an embedding.
2. Search the Qdrant `documents` collection for related document IDs.
3. Search the graph DB for document IDs connected to the question through folders and knowledge signals.
4. If document IDs were found, run chunk vector search inside those documents.
5. If no document IDs were found, run chunk vector search directly within the request `SearchScope`.
6. `ChunkRelevanceFilterAgent` removes chunks that are not related to the question.

The current Qdrant adapter implements dense chunk vectors, document-level vectors,
and folder vectors.

## Workflow Lifecycle

The workflow API lets AI-Core reason and propose actions while the app server keeps
control of source-data changes.

1. The app server calls `POST /tasks` with tenant and a natural-language request. AI-Core generates `task_id` and `task_request_id`.
2. A later `POST /tasks` with the same `task_id` appends another request to the same task instead of creating a new task.
3. `RunTaskUseCase` stores the current `TaskSnapshot` and calls the workflow runtime.
3. `PlanningAgent` turns the request into a `WorkflowPlan`.
4. `WorkflowPlanCompiler` turns the plan into executable steps.
5. `WorkflowStepExecutor` dispatches each step to a search, recommendation, generation, or host-action planning step.
6. Step results are recorded through `WorkflowArtifactRegistry` and exposed as app-server-visible `TaskOutput` values.
7. When a host action is created, the workflow saves a checkpoint and pauses.
8. The app server can remove a request entry through `DELETE /tasks/requests/{task_request_id}`.
9. The app server reports the action result through `POST /tasks/actions/result`, and the workflow resumes from the checkpoint.
10. When no steps or pending actions remain, the final `TaskSnapshot` is stored.

## Agents

An agent is an application-layer component responsible for one prompt-backed LLM
task. Agents depend on `LLMProvider` and `PromptStore`, not directly on the
OpenAI SDK.

| Agent | Prompt key | Used by | Responsibility |
| --- | --- | --- | --- |
| `PlanningAgent` | `workflow_planning` | `WorkflowEngine.prepare()` | Turn a natural-language task into a validated `WorkflowPlan`. |
| `DocumentProfilerAgent` | `document_profiling` | `IndexDocumentUseCase` | Create a `DocumentProfile` manifest and `KnowledgeSignal` set from a document and its chunks. |
| `ChunkRelevanceFilterAgent` | `chunk_relevance_filtering` | `FindDocumentsUseCase` | Keep only retrieved chunks related to the question. |
| `ContextGenerationAgent` | `answer_generation`, `summarization`, `draft_generation`, `ideas_exploration` | Retrieval and workflow generation steps | Generate cited text from retrieved chunks using a caller-selected prompt. |

Context generation agents render `UNTRUSTED_CONTEXT_INSTRUCTION` into prompts before
passing retrieved chunks to the LLM. The planner renders
`ALLOWED_WORKFLOW_ACTION_TYPES` so the model selects only actions supported by the
runtime.

## Domain Model

| Area | Key Models | Meaning |
| --- | --- | --- |
| Source snapshot | `SourceDocument`, `SourceFolder` | Current-state source data sent by the app server. Ownership does not transfer to AI-Core. |
| Retrieval/index model | `DocumentChunk`, `DocumentVectorProjection`, `FolderVectorProjection`, `RetrievedDocument`, `RetrievedFolder` | Store-specific projections and retrieval-facing references created by AI-Core. |
| AI profile | `DocumentProfile`, `KnowledgeSignal` | Profiling manifest plus signalized summary, concept, entity, issue, commitment, and claim outputs. |
| Retrieval | `RetrievalQuery`, `RequestContext`, `SearchScope`, `QueryAnchor` | Question text, tenant information, search scope, and anchor. |
| Generation | `GeneratedTextResult`, `DraftResult`, recommendation results, clarification results | Typed outputs produced by generation and recommendation steps. |
| Workflow | `TaskRequest`, `TaskSnapshot`, `TaskAnalysis`, `TaskOutput`, `TaskEvent` | Task state and outputs visible to the app server. |
| Host action | `HostAction`, `HostActionResult`, action input/output payload | Proposed source-data change that the app server must execute. |
| Knowledge graph | `DocumentRelationshipProjection`, `DocumentSignalGraphProjection`, `FolderRelationshipProjection` | Derived relationships between documents, folders, and knowledge signals. |
| Outbox event | `OutboxEvent` | Immutable projection input event emitted with PostgreSQL profile changes. |

Important rules:

- Source models are snapshots. The app server remains canonical.
- Vector projections and AI profiles are rebuildable derived state.
- Task outputs are typed. For example, a `summary` output must contain generated text.
- Host action payloads must match `HostActionType`.
- DTOs validate API input before mappers build use case commands and queries.

## Data Storage

AI-Core stores derived AI state only. It does not store canonical documents,
canonical folders, canonical tags, or permissions. Source tags may appear only as
opaque source metadata and are not promoted into graph or search scope.

### PostgreSQL

| Table | Primary Key | Stores |
| --- | --- | --- |
| `tenant_storage_scopes` | `tenant_id` | Tenant-level AI-Core storage lifecycle and retention scope. |
| `document_refs`, `folder_refs` | UUID refs | Source identities: `document_id` is the canonical document key and `(tenant_id, folder_id)` is the folder key. `document_type` is optional descriptive metadata only. |
| `source_document_snapshots`, `source_folder_snapshots` | UUID snapshots | Minimal snapshot manifests: source identity, digest, size, schema version, metadata, and timestamps. Raw source bodies and storage locations are not stored. |
| `document_index_records`, `document_chunk_sets`, `document_chunks`, `folder_index_records` | UUID records | Current and historical derived indexing manifests and chunk records. |
| `knowledge_signals` | `signal_id` | Extracted signal text, payload, evidence, confidence, extractor metadata, and source document/version scope. |
| `vector_projection_records` | UUID projection IDs | Qdrant write ledger. Records track collection, point ID, aggregate/subject identity, payload digest, projected/deleted timestamps, and retention state without source-row FKs. |
| `outbox_events` | `id` UUID | Kafka/Debezium transactional outbox events. `tenant_id`, `idempotency_key`, `sequence`, and `event_key` are used for stream ordering, idempotency, and dead-letter context. |
| `retrieval_runs`, `retrieval_results` | UUID run/result IDs | User-facing retrieval request history with query digest, scope, status, result ids, scores, and reasons. Query plaintext is not stored. |
| `tasks` | `task_id` UUID | Current task aggregate status, active request text, analysis message, current action, error, and metadata. |
| `task_requests` | `task_request_id` UUID | Ordered user request entries within a task, including active/removed status. |
| `task_outputs` | `output_id` UUID | Typed task outputs with result payloads and task-local ordering. |
| `host_actions` | `action_id` UUID | Proposed host actions with typed input payloads, result payloads, policy JSON, and task-local sequential ordering. |
| `task_events` | `event_id` UUID | Task event log. |

PostgreSQL schema is managed by Alembic. Run migrations before starting the API:

```bash
FOLDMIND_POSTGRES_DSN=postgresql://user:password@host:5432/foldmind_ai_core alembic upgrade head
```

The initial migration chain creates the optimized first-version derived-state
schema, Kafka outbox, the Qdrant vector ledger, and workflow task tables.

### Qdrant

| Setting | Default Collection | Payload Kind | Purpose |
| --- | --- | --- | --- |
| `FOLDMIND_QDRANT_DOCUMENT_CHUNK_COLLECTION` | `document_chunks` | `document_chunk` | Vector search over chunk text. |
| `FOLDMIND_QDRANT_DOCUMENT_COLLECTION` | `documents` | `document` | Document-level vector search over profile-enriched text. |
| `FOLDMIND_QDRANT_SIGNAL_COLLECTION` | `signals` | `signal` | Signal-level vector search over extracted knowledge signals. |
| `FOLDMIND_QDRANT_FOLDER_COLLECTION` | `folders` | `folder` | Folder metadata vector search for folder discovery and recommendations. |

### Graph DB

The graph DB is required for the standard AI-Core API. Document indexing and folder
indexing always write relationships to the graph DB.

| Relationship | Meaning |
| --- | --- |
| `Document` - `Folder` | Which folders contain a document. |
| `Document` - `Signal` | Which extracted knowledge signals are attached to a document version. |
| `Folder` - `Folder` | Folder hierarchy. |

Graph DB relationships are derived data for retrieval quality. The app server
remains the source of truth for folder structure, permissions, and tags.

### Workflow Checkpoints

Production workflow checkpoints are stored in PostgreSQL through
`FOLDMIND_WORKFLOW_CHECKPOINT_DSN` or `FOLDMIND_POSTGRES_DSN`. The in-memory checkpointer is
only for local/test configuration.

## Architecture

AI-Core follows a hexagonal architecture. The application layer depends on
interfaces (ports). Concrete technologies such as FastAPI, PostgreSQL, Qdrant,
the graph DB, the OpenAI SDK, and LangGraph live in adapter layers.

```text
FoldMind App Server
        |
        v
FastAPI inbound adapter
  routers + API DTOs
        |
        v
Application use cases
  indexing / retrieval / recommendation / workflow
        |
        +-- Domain models
        +-- Agents and prompt services
        +-- Workflow engine
        |
        v
Outbound ports
  LLMProvider / embeddings / vector stores / graph store / repositories / runtime
        |
        v
Outbound adapters
  OpenAI / PostgreSQL / Qdrant / graph DB / LangGraph / file prompts
```

| Package | Role |
| --- | --- |
| `core/domain/models/` | Business models. No external framework dependencies. |
| `core/domain/services/` | Pure domain rules such as concept normalization, confidence validation, and outbox invariants. |
| `core/application/ports/inbound/` | Use case contracts called by the app server. |
| `core/application/ports/outbound/` | Interfaces for LLM providers, embedding providers, PostgreSQL repositories, vector stores, graph store, prompt store, and workflow runtime. |
| `core/application/use_cases/` | Indexing, retrieval, recommendation, and workflow task orchestration. |
| `core/application/agents/` | Prompt-backed AI tasks. |
| `core/application/workflows/` | Workflow step execution, artifact storage, and host action result policy. |
| `adapters/inbound/http/` | FastAPI routers, REST DTOs, and HTTP error mapping. |
| `adapters/outbound/` | PostgreSQL, Qdrant, graph DB, OpenAI, LangGraph, and file prompt store implementations. |
| `bootstrap/` | Read settings and wire concrete adapters into use cases. |

## Deployment And Configuration

This repository uses endpoint-based configuration. There is no global
`DB_MODE=local/cloud` setting. Configure PostgreSQL, Qdrant, and the graph DB with
their own endpoints. Dockerfile and Compose manifests are not present yet.

```dotenv
FOLDMIND_POSTGRES_DSN=postgresql://user:password@host:5432/foldmind_ai_core

FOLDMIND_AI_PROVIDER=openai
FOLDMIND_OPENAI_API_KEY=sk-...
FOLDMIND_LLM_MODEL=gpt-4.1-mini
FOLDMIND_EMBEDDING_MODEL=text-embedding-3-small
FOLDMIND_EMBEDDING_VERSION=text-embedding-3-small
FOLDMIND_CHUNKING_VERSION=chunking-v1
FOLDMIND_INDEX_SCHEMA_VERSION=index-schema-v1
FOLDMIND_DOCUMENT_PROFILE_PROMPT_VERSION=document-profile-prompt-v1
FOLDMIND_EMBEDDING_DIMENSIONS=1536

FOLDMIND_QDRANT_URL=http://qdrant:6333
FOLDMIND_QDRANT_API_KEY=

FOLDMIND_NEO4J_URI=bolt://neo4j:7687
FOLDMIND_NEO4J_USER=neo4j
FOLDMIND_NEO4J_PASSWORD=password
```

`FOLDMIND_POSTGRES_DSN`, `FOLDMIND_QDRANT_URL`, `FOLDMIND_NEO4J_URI`, `FOLDMIND_NEO4J_USER`, `FOLDMIND_NEO4J_PASSWORD`,
`FOLDMIND_EMBEDDING_VERSION`, `FOLDMIND_CHUNKING_VERSION`, `FOLDMIND_INDEX_SCHEMA_VERSION`,
and `FOLDMIND_DOCUMENT_PROFILE_PROMPT_VERSION` are required for the standard
configured API.

Example environment files:

- `examples/env/local.env`: local self-hosted endpoint example.
- `examples/env/local-postgres-external-services.env`: local PostgreSQL with external
  Qdrant, graph DB, and Kafka endpoints.
- `examples/env/external.env`: external PostgreSQL, Qdrant, and graph DB endpoints.

## Package Layout

```text
foldmind-ai-core/
  scripts/         Local run and maintenance entrypoints
  src/foldmind_ai_core/
    main.py        Configured ASGI process entrypoint
    resources/     Runtime package data and bundled prompts
    bootstrap/     Settings, app factory, and container wiring
    core/
      domain/        Domain models and pure domain services
      application/   Use cases, ports, agents, and workflow policy
    adapters/      Inbound and outbound concrete adapters
    shared/        Shared primitive types and validation rules
  tests/
    unit/          Active unit tests
    contract/      Active app-server and schema contract tests
```

The package name is `foldmind_ai_core`.

## Development

```bash
python -m pip install -r requirements.txt
PYTHONPATH=src python -S -c "import foldmind_ai_core.core.domain; import foldmind_ai_core.core.application.ports"
PYTHONPATH=src python -m unittest discover -s tests
PYTHONPATH=src python -m compileall -q src tests
python -m pip install -e ".[dev]"
ruff check src tests
mypy src
```

`scripts/run_api.sh` starts the configured ASGI app. `scripts/run_worker.sh`
starts the Kafka outbox projection worker.

Run one outbox worker per `FOLDMIND_OUTBOX_PROJECTION_TARGET`: `qdrant-document-chunks`,
`qdrant-documents`, `qdrant-signals`, `qdrant-folders`, or `neo4j-graph`. The worker always derives
a target-specific consumer group name so each projection target consumes the same
outbox stream independently.
The default outbox topic is `indexing-events`; configure Debezium so the Kafka
message key is the `event_key` column. Failed messages are published to
`indexing-events.dlq`; replay them with `scripts/replay_dead_letter_events.py` after fixing the
underlying failure.

For local workflow bootstrap without a separate checkpoint DSN, set
`FOLDMIND_ALLOW_IN_MEMORY_WORKFLOW_CHECKPOINT=true`. The standard configured API
still requires `FOLDMIND_POSTGRES_DSN`, `FOLDMIND_QDRANT_URL`, and graph DB settings.

## Current Limitations

- Dockerfile and Compose manifests are not present yet.
