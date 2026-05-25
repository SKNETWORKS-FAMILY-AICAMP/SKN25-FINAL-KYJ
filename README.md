# FoldMind-AI-Core

[한국어 README](README.ko.md)

FoldMind-AI-Core is the AI processing server that runs beside the FoldMind app
server. The app server remains the owner of source documents, folders,
permissions, users, and business rules. AI-Core receives current-state snapshots
from the app server and stores only derived AI data: search payloads, document
index records and signals, lightweight folder metadata indexes, graph relationships, workflow
snapshots, and task events.

AI-Core does not replace the app server database. It does not store or mutate
canonical source data.

## At A Glance

| Area | What Happens |
| --- | --- |
| Document indexing | Split document text into chunks, create document index records and signals, and emit outbox events for asynchronous vector and graph projections. |
| Folder indexing | Store lightweight folder index state and emit outbox events for asynchronous folder vector and graph hierarchy projections. |
| Document search | Convert the question into an embedding, then use the vector DB and graph DB together to find evidence chunks. |
| Answer generation | Send retrieved chunks to the LLM and return generated text with citations. |
| Workflow tasks | Break a natural-language request into steps, execute AI work, and return source-data changes as host actions for the app server. |
| Persistence scope | Store document index records, document signals, vector payloads, graph relationships, task snapshots, and task events. Do not store canonical source data. |

## Responsibility Boundary

| Owner | Owns |
| --- | --- |
| FoldMind app server | Source documents, source folders, source tags, permissions, users, and business rules. |
| AI-Core | Document index records, document signals, vector index payloads, graph DB relationships, retrieval results, generated outputs, workflow state, and proposed host actions. |

AI-Core does not call the app server directly. When a task needs to create a folder,
move a document, or perform another source-data change, AI-Core returns a
`HostAction`. The app server approves, executes, rejects, or modifies that action
and reports the result back to AI-Core.

## Main Capabilities

**Document Indexing**

The app server sends a `SourceDocument` snapshot. AI-Core splits the body into
searchable `DocumentChunk` records. AI-Core stores a `DocumentIndexRecord` for
the current digest state, and the LLM creates extracted `DocumentSignal` records
for summary, concept, entity, issue, commitment, and claim evidence.

Indexing writes the index record, signals, and an outbox event atomically to PostgreSQL.
Debezium Kafka consumers asynchronously create embeddings and project Qdrant and
graph DB state. Outbox events carry a database-generated sequence, idempotency
key, and generated `partition_key` for stream ordering, idempotency, and
dead-letter context. Delete event idempotency keys include the current
`source_version` so a later reindex/delete cycle is not swallowed as a duplicate.
Qdrant stores chunk, signal, folder, and document-level
vectors. The graph DB stores document-to-folder, document-to-signal,
folder-to-signal, and folder hierarchy relationships. Neo4j projection state is not mirrored in
PostgreSQL; recovery uses outbox replay plus Kafka dead-letter handling. Chunk
text stays in Qdrant; chunk nodes are not projected into the graph DB.

**Folder Indexing**

The app server sends a `SourceFolder` snapshot. AI-Core reads folder metadata and
stores it as a lightweight derived index. It emits an outbox event so projection
workers embed the folder name, path, and description into the Qdrant folder
collection and project a `Folder` node plus folder hierarchy edges into the graph
DB.

Folder indexing does not create or store a PostgreSQL folder profile. Folder names,
paths, descriptions, and hierarchy records are rebuildable search indexes; the app
server remains canonical for folder display data and permissions.

**Document Search**

Document search is an application service used by workflow steps.

1. Qdrant finds chunks and documents that are semantically close to the question.
2. PostgreSQL keyword search contributes lexical chunk matches.
3. The graph DB finds documents linked through folders and extracted signals.
4. AI-Core merges dense, keyword, document-level, and graph signals into ranked chunks.

**Question Answering**

Question answering runs as a workflow task. The workflow searches relevant
documents, formats retrieved context for the LLM, and returns generated text with
citations in the task result.

**Recommendations**

Folder recommendations run through workflow recommendation steps. AI-Core returns
candidate folder IDs with scores and reasons; the app server remains responsible
for applying any source-data change.

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
| AI-Core creates signals | The LLM generates summary, concept, entity, issue, commitment, and claim signals. |
| AI-Core stores derived data | PostgreSQL receives the index records and transactional outbox events. |
| Projection workers run | Outbox consumers create embeddings and project Qdrant and graph DB records. |
| App server receives | The indexed chunk count. The source document remains owned by the app server. |

### 2. Answer A Question With A Task

| Step | What Happens |
| --- | --- |
| App server sends | `POST /tasks` with a natural-language question, tenant, and optional context. |
| AI-Core finds document IDs | Qdrant document vectors and graph DB relationship search find related document IDs. |
| AI-Core finds chunks | Chunks are searched inside those documents. If no document IDs are found, chunk search runs directly within the requested scope. |
| AI-Core generates an answer | The context generation agent writes an answer from retrieved context. |
| App server receives | A task snapshot containing answer text and citations. |

### 3. Run A Workflow Task

| Step | What Happens |
| --- | --- |
| App server starts | `POST /tasks` with tenant and a natural-language request. AI-Core generates the task ID and first task input ID. |
| App server continues | `POST /tasks/{task_id}/inputs` appends another input to the same task. |
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
| `DELETE` | `/indexing/documents/{document_id}` | - | `204 No Content` | Delete the document index record, signals, vector payloads, and graph DB relationships. |
| `POST` | `/indexing/folders` | `IndexFolderRequest` | `IndexFolderResponse` | Index a folder snapshot and return the searchable folder model. |
| `DELETE` | `/indexing/folders/{folder_id}` | - | `204 No Content` | Delete the folder vector payloads and graph DB relationships. |

### Retrieval And Recommendations

Document, signal, and folder retrieval are application services used by workflow
steps. They are not exposed as standalone HTTP routes in the current API.

### Workflow Tasks

| Method | Path | Request DTO | Response DTO | Purpose |
| --- | --- | --- | --- | --- |
| `POST` | `/tasks` | `CreateTaskRequest` | `TaskSnapshotResponse` | Start a task from a natural-language input. |
| `POST` | `/tasks/{task_id}/inputs` | `AppendTaskInputRequest` | `TaskSnapshotResponse` | Append a natural-language input to an existing task and replan. |
| `GET` | `/tasks/{task_id}` | - | `TaskSnapshotResponse` | Read the latest task snapshot visible to the app server. |
| `DELETE` | `/tasks/inputs/{task_input_id}` | - | `TaskSnapshotResponse` | Mark an input entry as removed and replan from the active inputs. |
| `POST` | `/tasks/actions/result` | `RecordHostActionResultRequest` | `RecordHostActionResultResponse` | Resume a paused workflow after the app server reports a host action result. |

## Search Behavior

Document search is implemented by `DocumentSearchService`.

1. Convert the question text into an embedding.
2. Search the Qdrant `documents` collection for related document IDs.
3. Search the graph DB for document IDs connected to the question through folders and extracted signals.
4. If document IDs were found, run chunk vector search inside those documents.
5. If no document IDs were found, run chunk vector search directly within the request `SearchScope`.
6. Hybrid retrieval merges dense and keyword results, applies document-level boosts, and returns the highest ranked chunks.

The current Qdrant adapter implements dense chunk vectors, document-level vectors,
and folder vectors.

## Workflow Lifecycle

The workflow API lets AI-Core reason and propose actions while the app server keeps
control of source-data changes.

1. The app server calls `POST /tasks` with tenant and a natural-language input. AI-Core generates `task_id` and `task_input_id`.
2. A later `POST /tasks/{task_id}/inputs` appends another input to the same task.
3. `TaskWorkflowService` stores the current `TaskSnapshot` and calls the workflow runtime.
4. `PlanningAgent` turns the request into a `WorkflowPlan`.
5. `WorkflowPlanCompiler` turns the plan into executable steps.
6. `WorkflowStepExecutor` dispatches each step to a search, recommendation, generation, or host-action planning step.
7. Step results are recorded through `WorkflowArtifactRegistry` and exposed as app-server-visible `TaskFinalResult` values.
8. When a host action is created, the workflow saves a checkpoint and pauses.
9. The app server can remove an input entry through `DELETE /tasks/inputs/{task_input_id}`.
10. The app server reports the action result through `POST /tasks/actions/result`, and the workflow resumes from the checkpoint.
11. When no steps or pending actions remain, the final `TaskSnapshot` is stored.

## Agents

An agent is an application-layer component responsible for one prompt-backed LLM
task. Agents depend on `LLMProvider` and `PromptStore`, not directly on the
OpenAI SDK.

| Agent | Prompt key | Used by | Responsibility |
| --- | --- | --- | --- |
| `PlanningAgent` | `workflow_planning` | `WorkflowEngine.prepare()` | Turn a natural-language task into a validated `WorkflowPlan`. |
| `DocumentSignalExtractorAgent` | `document_signal_extraction` | `DocumentIndexingService` | Create a `DocumentIndexRecord` and `DocumentSignal` set from a document and its chunks. |
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
| Signals | `DocumentSignal`, `FolderSignal` | Signalized summary, concept, entity, issue, commitment, and claim outputs. |
| Retrieval | `RetrievalQuery`, `RequestContext`, `SearchScope`, `QueryAnchor` | Question text, tenant information, search scope, and anchor. |
| Generation | `GeneratedTextResult`, `DraftResult`, recommendation results, clarification results | Typed outputs produced by generation and recommendation steps. |
| Workflow | `TaskInputEntry`, `TaskSnapshot`, `TaskAnalysis`, `TaskFinalResult`, `TaskEvent` | Task input history, state, and outputs visible to the app server. |
| Host action | `HostAction`, `HostActionResult`, action input/output payload | Proposed source-data change that the app server must execute. |
| Knowledge graph | `DocumentRelationshipProjection`, `DocumentSignalGraphProjection`, `FolderRelationshipProjection` | Derived relationships between documents, folders, and document/folder signals. |
| Outbox event | `OutboxEvent` | Immutable projection input event emitted with PostgreSQL index record and signal changes. |

Important rules:

- Source models are snapshots. The app server remains canonical.
- Vector projections, index records, and signals are rebuildable derived state.
- Task outputs are typed. For example, a `summary` output must contain generated text.
- Host action payloads must match `HostActionType`.
- DTOs validate API input before mappers build application commands and queries.

## Data Storage

AI-Core stores derived AI state only. It does not store canonical documents,
canonical folders, canonical tags, or permissions. Source tags may appear only as
opaque source metadata and are not promoted into graph or search scope.

### PostgreSQL

| Table | Primary Key | Stores |
| --- | --- | --- |
| `tenant_storage_scopes` | `tenant_id` | Tenant-level AI-Core storage lifecycle and retention scope. |
| `document_sources`, `folder_sources` | Source IDs | Current source manifests: source identity, aggregate source version, digest/size or folder metadata, timestamps, deletion state, and opaque source metadata. Raw source bodies are not stored. |
| `source_document_folder_relations` | `(tenant_id, document_id, folder_id)` | Current folder membership rows from document relation snapshots. An empty row set is the current empty membership. |
| `document_index_records`, `document_chunks`, `folder_index_records` | Source IDs / chunk UUIDs | Current derived indexing manifests and document chunk records. |
| `document_signals`, `folder_signals` | `signal_id` | Extracted signal text, payload, evidence, confidence, extractor metadata, source input digest, generation version, and optional generation model. |
| `vector_projection_records` | `(collection_name, point_id)` | Qdrant write ledger. Records track collection, point ID, source identity, vector item identity, source input digest, and vector input digest without source-row FKs. |
| `outbox_events` | `event_id` UUID | Kafka/Debezium transactional outbox events. `tenant_id`, `idempotency_key`, `event_sequence`, `partition_key`, and `event_type` are used for stream ordering, idempotency, and dead-letter context. |
| `tasks` | `task_id` UUID | Current task aggregate status, active input text, analysis message, current action, error, and metadata. |
| `task_inputs` | `task_input_id` UUID | Ordered user request entries within a task, including active/removed status. |
| `task_jobs`, `task_job_results` | UUID job/result IDs | Planned workflow jobs, execution state, typed result payloads, and task-local ordering. |
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
| `FOLDMIND_QDRANT_DOCUMENT_COLLECTION` | `documents` | `document` | Document-level vector search over source text and signal-derived context. |
| `FOLDMIND_QDRANT_SIGNAL_COLLECTION` | `signals` | `signal` | Signal-level vector search over extracted document and folder signals. |
| `FOLDMIND_QDRANT_FOLDER_COLLECTION` | `folders` | `folder` | Folder metadata vector search for folder discovery and recommendations. |

### Graph DB

The graph DB is required for the standard AI-Core API. Document indexing and folder
indexing always write relationships to the graph DB.

| Relationship | Meaning |
| --- | --- |
| `Document` - `Folder` | Which folders contain a document. |
| `Document` - `Signal` | Which extracted signals are attached to a document version. |
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
Inbound application ports
  typed protocols for HTTP and messaging entrypoints
        |
        v
Application services
  indexing / projection / workflow entrypoints
  retrieval and recommendation policies live in services + workflow steps
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
| `core/application/ports/inbound/` | Protocols that inbound adapters call. Concrete application services implement these structurally. |
| `core/application/ports/outbound/` | Interfaces for LLM providers, embedding providers, PostgreSQL repositories, vector stores, graph store, prompt store, and workflow runtime. |
| `core/application/models/` | Application service commands, queries, results, retrieval models, projection models, and workflow flow-state models. |
| `core/application/mappers/` | Boundary and domain-to-application mapping functions. |
| `core/application/services/` | Inbound application API and application policies grouped by indexing, retrieval, recommendation, projection, and workflow responsibility. |
| `core/application/formatters/`, `execution/`, `prompts.py` | Application support code that is not itself a service. |
| `core/application/agents/` | Prompt-backed AI tasks. |
| `core/application/workflows/` | Workflow step execution, artifact storage, and host action result policy. |
| `adapters/inbound/http/` | FastAPI routers, REST DTOs, and HTTP error mapping. |
| `adapters/outbound/` | PostgreSQL, Qdrant, graph DB, OpenAI, LangGraph, and file prompt store implementations. |
| `bootstrap/` | Read settings and wire concrete adapters and application services behind their ports. |

## Deployment And Configuration

This repository uses endpoint-based configuration. There is no global
`DB_MODE=local/cloud` setting. Configure PostgreSQL, Qdrant, and the graph DB with
their own endpoints. Dockerfile and Compose manifests are not present yet.

```dotenv
FOLDMIND_POSTGRES_DSN=postgresql://user:password@host:5432/foldmind_ai_core
PURGE_AFTER_DAYS=90

FOLDMIND_AI_PROVIDER=openai
FOLDMIND_OPENAI_API_KEY=sk-...
FOLDMIND_LLM_MODEL=gpt-4.1-mini
FOLDMIND_EMBEDDING_MODEL=text-embedding-3-small
FOLDMIND_EMBEDDING_VERSION=text-embedding-3-small
FOLDMIND_CHUNKING_VERSION=chunking-v1
FOLDMIND_INDEX_SCHEMA_VERSION=index-schema-v1
FOLDMIND_DOCUMENT_SIGNAL_EXTRACTION_PROMPT_VERSION=document-signal-extraction-prompt-v1
FOLDMIND_EMBEDDING_DIMENSIONS=1536

FOLDMIND_QDRANT_URL=http://qdrant:6333
FOLDMIND_QDRANT_API_KEY=

FOLDMIND_NEO4J_URI=bolt://neo4j:7687
FOLDMIND_NEO4J_USER=neo4j
FOLDMIND_NEO4J_PASSWORD=password
```

`FOLDMIND_POSTGRES_DSN`, `FOLDMIND_QDRANT_URL`, `FOLDMIND_NEO4J_URI`, `FOLDMIND_NEO4J_USER`, `FOLDMIND_NEO4J_PASSWORD`,
`FOLDMIND_EMBEDDING_VERSION`, `FOLDMIND_CHUNKING_VERSION`, `FOLDMIND_INDEX_SCHEMA_VERSION`,
and `FOLDMIND_DOCUMENT_SIGNAL_EXTRACTION_PROMPT_VERSION` are required for the standard
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
      application/   Services, ports, agents, and workflow policy
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
message key is the generated `partition_key` column. Failed messages are published to
`indexing-events.dlq`; replay them with `scripts/replay_dead_letter_events.py` after fixing the
underlying failure.

For local workflow bootstrap without a separate checkpoint DSN, set
`FOLDMIND_ALLOW_IN_MEMORY_WORKFLOW_CHECKPOINT=true`. The standard configured API
still requires `FOLDMIND_POSTGRES_DSN`, `FOLDMIND_QDRANT_URL`, and graph DB settings.

## Current Limitations

- Dockerfile and Compose manifests are not present yet.
