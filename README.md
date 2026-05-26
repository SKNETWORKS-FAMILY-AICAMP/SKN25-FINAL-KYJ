# FoldMind-AI-Core

[한국어 README](README.ko.md)

FoldMind-AI-Core is the AI processing server that runs beside the FoldMind app
server. The app server remains the owner of source documents, folders,
permissions, users, and business rules. AI-Core receives current-state snapshots
from the app server and stores lightweight source manifests plus AI-derived data:
search payloads, document index records and signals, folder index records, graph
relationships, workflow snapshots, and task events.

AI-Core does not replace the app server database. It does not store raw document
bodies or mutate canonical source data.

## At A Glance

- **Document indexing:** split document text into chunks, create index records and
  signals, and emit outbox events for vector/graph projections.
- **Folder indexing:** store lightweight folder index state and emit outbox events
  for folder vector and hierarchy projections.
- **Document search:** combine vector search, keyword search, and graph search to
  find evidence chunks.
- **Answer generation:** send retrieved chunks to the LLM and return generated text
  with citations.
- **Workflow tasks:** break a natural-language request into steps, execute AI work,
  and return source-data changes as host actions.
- **Persistence scope:** store source manifests, relation rows, derived index data,
  vector/graph projections, task state, and task events. Do not store canonical
  source data.

## Responsibility Boundary

- **FoldMind app server:** source documents, source folders, source tags,
  permissions, users, and business rules.
- **AI-Core:** source manifests for freshness checks, derived index data,
  vector/graph projections, retrieval results, generated outputs, workflow
  state, and proposed host actions.

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

Indexing writes the following state atomically inside a PostgreSQL transaction.

- source manifest
- optional folder relation snapshot
- index record
- signals
- outbox events

A supplied folder relation snapshot must match the document `source_version`.
An empty snapshot is the current empty membership. An omitted snapshot leaves
membership unchanged.

Outbox events carry a database-generated sequence, idempotency key, and generated
`partition_key`. Delete event idempotency keys include the current
`source_version`, so a later reindex/delete cycle is not swallowed as a
duplicate.

Debezium Kafka consumers read outbox events and asynchronously create embeddings
and projections.

- Qdrant stores chunk, signal, folder, and document-level vectors.
- The graph DB stores `Document`-`Folder`, `Document`-`DocumentSignal`,
  `Folder`-`FolderSignal`, `FolderSignal`-`Document`, and folder hierarchy
  relationships.
- Neo4j projection state is not mirrored in a PostgreSQL ledger.
  Recovery uses outbox replay plus Kafka dead-letter handling.
- Chunk text stays in Qdrant.
  Chunk nodes are not projected into the graph DB.

**Folder Indexing**

The app server sends a `SourceFolder` snapshot. AI-Core reads folder metadata and
stores it as a lightweight derived index. It emits an outbox event so projection
workers embed the folder name, path, and description into the Qdrant folder
collection and project a `Folder` node plus folder hierarchy edges into the graph
DB.

Folder indexing stores `folder_sources` and `folder_index_records`, not a
separate descriptive folder table. Folder names, paths, descriptions, and
hierarchy records are rebuildable search indexes; the app server remains
canonical for folder display data and permissions.

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

Folder recommendations run through workflow recommendation steps.
AI-Core returns candidate folder IDs with scores and reasons.
The app server remains responsible for applying any source-data change.

**Workflow Tasks**

`/tasks` receives a natural-language request.

AI-Core turns the request into steps such as:

- search
- recommendation
- summary
- answer generation
- draft generation
- idea generation
- host-action planning

AI-Core executes AI-only steps itself.
For source-data changes, it returns a `HostAction` and waits for the app server
to report the result.

## Typical App-Server Flows

### 1. Index A Document

1. The app server sends `POST /indexing/documents` with title, body,
   aggregate `source_version`, metadata, and optional
   `folder_relation_snapshot.folder_ids`.
2. AI-Core validates tenant, source identity, version, and indexable text.
3. AI-Core splits the body into `DocumentChunk` records.
4. The LLM generates summary, concept, entity, issue, commitment, and claim
   signals.
5. PostgreSQL stores the source manifest, supplied relation rows, index record,
   signals, and transactional outbox events.
6. Projection workers create embeddings and project Qdrant and graph DB records.
7. The app server receives the indexed chunk count.
8. Source ownership remains with the app server.

### 2. Answer A Question With A Task

1. The app server sends `POST /tasks` with a natural-language question, tenant,
   and optional context.
2. AI-Core finds related document IDs through Qdrant document vectors and graph
   relationships.
3. AI-Core searches chunks inside those documents.
4. If no document IDs are found, chunk search runs within the requested scope.
5. The context generation agent writes an answer from retrieved context.
6. The app server receives a task snapshot containing answer text and citations.

### 3. Run A Workflow Task

1. The app server starts with `POST /tasks`.
2. AI-Core generates the task ID and first task input ID.
3. The app server can append input with `POST /tasks/{task_id}/inputs`.
4. The planning agent turns active requests into executable workflow steps.
5. AI-Core runs search, recommendation, summary, answer, draft, and idea steps.
6. Source-data changes are returned as `HostAction` values in the task snapshot.
7. The app server approves, executes, rejects, modifies, skips, or retries each
   action.
8. The app server reports action results through `POST /tasks/actions/result`.
9. AI-Core resumes from the saved checkpoint and returns the latest task snapshot.

## REST API

All REST DTOs reject unknown fields.

- Input validation errors return `422`.
- Missing tasks or recommendation targets return `404` on routes that handle
  those cases.

### System

- `GET /health`
  Checks that the process is running.
  Normal response: `{"status": "ok"}`.

### Indexing

- `POST /indexing/documents`
  Request: `IndexDocumentRequest`.
  Response: `IndexDocumentResponse`.
  Indexes a document snapshot and returns the created chunk count.
- `DELETE /indexing/documents/{document_id}`
  Response: `204 No Content`.
  Marks the source manifest deleted and removes derived document state.
- `POST /indexing/folders`
  Request: `IndexFolderRequest`.
  Response: `IndexFolderResponse`.
  Indexes a folder snapshot and returns the searchable folder model.
- `DELETE /indexing/folders/{folder_id}`
  Response: `204 No Content`.
  Marks folder source/index state deleted and removes derived folder state.

### Retrieval And Recommendations

Document, signal, and folder retrieval are application services used by workflow
steps.

They are not exposed as standalone HTTP routes in the current API.

### Workflow Tasks

- `POST /tasks`
  Request: `CreateTaskRequest`.
  Response: `TaskSnapshotResponse`.
  Starts a task from natural-language input.
- `POST /tasks/{task_id}/inputs`
  Request: `AppendTaskInputRequest`.
  Response: `TaskSnapshotResponse`.
  Appends input to an existing task and replans.
- `GET /tasks/{task_id}`
  Response: `TaskSnapshotResponse`.
  Reads the latest app-server-visible task snapshot.
- `DELETE /tasks/inputs/{task_input_id}`
  Response: `TaskSnapshotResponse`.
  Marks an input entry as removed and replans from active inputs.
- `POST /tasks/actions/result`
  Request: `RecordHostActionResultRequest`.
  Response: `RecordHostActionResultResponse`.
  Resumes a paused workflow after a host action result.

## Search Behavior

Document search is implemented by `DocumentSearchService` and the lower-level
retrieval services it coordinates.

1. Convert the question text into an embedding.
2. Search the Qdrant `documents` collection for related document IDs.
3. Search the graph DB for document IDs connected through folders and extracted
   signals.
4. If document IDs were found, run chunk vector search inside those documents.
5. If no document IDs were found, run chunk vector search directly within the
   request `SearchScope`.
6. Hybrid retrieval merges dense and keyword results, applies document-level
   boosts, and returns the highest ranked chunks.

The current Qdrant adapter implements dense chunk vectors, document-level vectors,
signal vectors, and folder vectors.

## Workflow Lifecycle

The workflow API lets AI-Core reason and propose actions while the app server keeps
control of source-data changes.

**Start and replan**

1. The app server calls `POST /tasks` with tenant and natural-language input.
2. AI-Core generates `task_id` and `task_input_id`.
3. A later `POST /tasks/{task_id}/inputs` appends input to the same task.

**Plan and execute**

1. `TaskWorkflowService` stores the current `TaskSnapshot`.
2. The service calls the workflow runtime.
3. `PlanningAgent` turns active requests into a `WorkflowPlan`.
4. `WorkflowPlanCompiler` turns the plan into executable steps.
5. `WorkflowStepExecutor` dispatches each step to search, recommendation,
   generation, or host-action planning.
6. `WorkflowArtifactRegistry` records step results as app-server-visible
   `TaskFinalResult` values.

**Pause, resume, and finish**

1. When a host action is created, the workflow saves a checkpoint and pauses.
2. The app server can remove an input entry through
   `DELETE /tasks/inputs/{task_input_id}`.
3. The app server reports action results through `POST /tasks/actions/result`.
4. AI-Core resumes the workflow from the checkpoint.
5. When no steps or pending actions remain, the final `TaskSnapshot` is stored.

## Agents

An agent is an application-layer component responsible for one prompt-backed LLM
task. Agents depend on `LLMProvider` and `PromptStore`, not directly on the
OpenAI SDK.

- `PlanningAgent`
  Uses `workflow_planning` in `WorkflowEngine.prepare()`.
  Turns a natural-language task into a validated `WorkflowPlan`.
- `DocumentSignalExtractorAgent`
  Uses `document_signal_extraction` in `DocumentIndexingService`.
  Creates a `DocumentIndexRecord` and `DocumentSignal` set from a document and its
  chunks.
- `ContextGenerationAgent`
  Uses `answer_generation`, `summarization`, `draft_generation`, and
  `ideas_exploration` in retrieval and workflow generation steps.
  Generates cited text from retrieved chunks.

Context generation agents render `UNTRUSTED_CONTEXT_INSTRUCTION` into prompts before
passing retrieved chunks to the LLM. The planner renders
`ALLOWED_WORKFLOW_ACTION_TYPES` so the model selects only actions supported by the
runtime.

## Domain Model

- **Source snapshot:** `SourceDocument`, `SourceFolder`.
  Current-state source data sent by the app server.
- **Retrieval/index model:** `DocumentChunk`, vector projection models,
  `RetrievedDocument`, `RetrievedFolder`.
  Store-specific projections and retrieval-facing references.
- **Signals:** `DocumentSignal`, `FolderSignal`.
  Summary, concept, entity, issue, commitment, and claim outputs.
- **Retrieval:** `RetrievalQuery`, `RequestContext`, `SearchScope`, `QueryAnchor`.
  Question text, tenant information, search scope, and anchor.
- **Generation:** `GeneratedTextResult`, `DraftResult`, recommendation results,
  and clarification results.
- **Workflow:** `TaskInputEntry`, `TaskSnapshot`, `TaskAnalysis`,
  `TaskFinalResult`, `TaskEvent`.
- **Host action:** `HostAction`, `HostActionResult`, and typed action payloads.
- **Graph projection:** `ProjectDocumentCommand`,
  `ProjectDocumentFolderRelationsCommand`, `ProjectFolderCommand`,
  `ProjectFolderSignalsCommand`.
- **Outbox event:** `OutboxEvent`.
  Immutable projection input emitted with PostgreSQL source, relation, index, and
  signal changes.

Important rules:

- Source models are snapshots.
- The app server remains canonical.
- Vector projections, index records, and signals are rebuildable derived state.
- Task outputs are typed.
- For example, a `summary` output must contain generated text.
- Host action payloads must match `HostActionType`.
- DTOs validate API input before mappers build application commands and queries.

## Data Storage

AI-Core stores derived AI state only. It does not store canonical documents,
canonical folders, canonical tags, or permissions. Source tags may appear only as
opaque source metadata and are not promoted into graph or search scope.

### PostgreSQL

- **`tenant_storage_scopes`** (`tenant_id`):
  tenant-level AI-Core storage lifecycle and retention scope.
- **`document_sources`, `folder_sources`** (source IDs):
  current source manifests.
  They store source identity, aggregate source version, digest/size or folder
  metadata, timestamps, deletion state, and opaque source metadata.
  Raw source bodies are not stored.
- **`source_document_folder_relations`**
  (`tenant_id`, `document_id`, `folder_id`):
  current folder membership rows from document relation snapshots. An empty row
  set is the current empty membership.
- **`document_index_records`, `document_chunks`, `folder_index_records`**
  (source IDs / chunk UUIDs):
  current derived indexing manifests and document chunk records.
- **`document_signals`, `folder_signals`** (`signal_id`):
  extracted signal text, payload, evidence, confidence, extractor metadata,
  document/folder signal input digest, generation version, and optional
  generation model.
- **`vector_projection_records`** (`collection_name`, `point_id`):
  Qdrant write ledger. Records track collection, point ID, source identity,
  vector item identity, source input digest, and vector input digest without
  source-row foreign keys.
- **`outbox_events`** (`event_id` UUID):
  Kafka/Debezium transactional outbox events. `tenant_id`, `idempotency_key`,
  `event_sequence`, `partition_key`, and `event_type` support stream ordering,
  idempotency, and dead-letter context.
- **`tasks`** (`task_id` UUID):
  current task aggregate status, active input text, analysis message, current
  action, error, and metadata.
- **`task_inputs`** (`task_input_id` UUID):
  ordered user request entries within a task, including active/removed status.
- **`task_jobs`, `task_job_results`** (UUID job/result IDs):
  planned workflow jobs, execution state, typed result payloads, and task-local
  ordering.
- **`host_actions`** (`action_id` UUID):
  proposed host actions with typed input payloads, result payloads, policy JSON,
  and task-local sequential ordering.
- **`task_events`** (`event_id` UUID):
  task event log.

PostgreSQL schema is managed by Alembic. Run migrations before starting the API:

```bash
FOLDMIND_POSTGRES_DSN=postgresql://user:password@host:5432/foldmind_ai_core alembic upgrade head
```

The initial migration chain creates the optimized first-version derived-state
schema, Kafka outbox, the Qdrant vector ledger, and workflow task tables.

### Qdrant

- **`FOLDMIND_QDRANT_DOCUMENT_CHUNK_COLLECTION`**
  - Default collection: `document_chunks`
  - Payload kind: `document_chunk`
  - Purpose: vector search over chunk text.
- **`FOLDMIND_QDRANT_DOCUMENT_COLLECTION`**
  - Default collection: `documents`
  - Payload kind: `document`
  - Purpose: document-level vector search over document title and extracted
    signal text.
- **`FOLDMIND_QDRANT_SIGNAL_COLLECTION`**
  - Default collection: `signals`
  - Payload kind: `signal`
  - Purpose: signal-level vector search over extracted document and folder
    signals.
- **`FOLDMIND_QDRANT_FOLDER_COLLECTION`**
  - Default collection: `folders`
  - Payload kind: `folder`
  - Purpose: folder metadata vector search for folder discovery and
    recommendations.

### Graph DB

The graph DB is required for the standard AI-Core API. Indexing requests do not
write it synchronously; projection workers consume outbox events and update graph
relationships idempotently.

- **`Document`-`Folder` (`IN_FOLDER`):** which folders contain a document.
- **`Document`-`DocumentSignal` (`HAS_SIGNAL`):** extracted document signals
  attached to a document version.
- **`Folder`-`Folder` (`CHILD_OF`):** folder hierarchy.
- **`Folder`-`FolderSignal` (`HAS_SIGNAL`):** folder-derived signals attached
  to a folder.
- **`FolderSignal`-`Document` (`ABOUT_DOCUMENT`):** optional related document
  edge for folder-derived signals that point at a document.

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

- **`core/domain/models/`:** business models with no external framework
  dependencies.
- **`core/domain/services/`:** pure domain rules such as concept normalization,
  confidence validation, and outbox invariants.
- **`core/application/ports/inbound/`:** protocols called by inbound adapters.
  Concrete application services implement these structurally.
- **`core/application/ports/outbound/`:** interfaces for LLM providers,
  embedding providers, repositories, vector stores, graph store, prompt store,
  and workflow runtime.
- **`core/application/models/`:** application service commands, queries,
  results, retrieval models, projection models, and workflow flow-state models.
- **`core/application/mappers/`:** boundary and domain-to-application mapping
  functions.
- **`core/application/services/`:** inbound application APIs and application
  policies grouped by indexing, retrieval, recommendation, projection, and
  workflow responsibility.
- **`core/application/formatters/`, `execution/`, `prompts.py`:** application
  support code that is not itself a service.
- **`core/application/agents/`:** prompt-backed AI tasks.
- **`core/application/workflows/`:** workflow step execution, artifact storage,
  and host action result policy.
- **`adapters/inbound/http/`:** FastAPI routers, REST DTOs, and HTTP error
  mapping.
- **`adapters/outbound/`:** PostgreSQL, Qdrant, graph DB, OpenAI, LangGraph, and
  file prompt store implementations.
- **`bootstrap/`:** read settings and wire concrete adapters and application
  services behind their ports.

## Deployment And Configuration

This repository uses endpoint-based configuration.

- There is no global `DB_MODE=local/cloud` setting.
- PostgreSQL, Qdrant, and the graph DB each use their own endpoint.
- Dockerfile and Compose manifests are not present yet.

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
FOLDMIND_QDRANT_DOCUMENT_CHUNK_COLLECTION=document_chunks
FOLDMIND_QDRANT_DOCUMENT_COLLECTION=documents
FOLDMIND_QDRANT_SIGNAL_COLLECTION=signals
FOLDMIND_QDRANT_FOLDER_COLLECTION=folders

FOLDMIND_NEO4J_URI=bolt://neo4j:7687
FOLDMIND_NEO4J_USER=neo4j
FOLDMIND_NEO4J_PASSWORD=password
```

`FOLDMIND_POSTGRES_DSN`, `FOLDMIND_QDRANT_URL`, `FOLDMIND_NEO4J_URI`,
`FOLDMIND_NEO4J_USER`, `FOLDMIND_NEO4J_PASSWORD`, `FOLDMIND_OPENAI_API_KEY`
when `FOLDMIND_AI_PROVIDER=openai`, `FOLDMIND_EMBEDDING_MODEL`,
`FOLDMIND_EMBEDDING_VERSION`, `FOLDMIND_CHUNKING_VERSION`,
`FOLDMIND_INDEX_SCHEMA_VERSION`, and
`FOLDMIND_DOCUMENT_SIGNAL_EXTRACTION_PROMPT_VERSION` are required for the
standard configured API.

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
PYTHONPATH=src python -m compileall -q src tests migrations scripts
PYTHONPATH=src python -m unittest discover -s tests
python -m pip install -e ".[dev]"
ruff check src tests
mypy src
```

- `scripts/run_api.sh` starts the configured ASGI app.
- `scripts/run_worker.sh` starts the Kafka outbox projection worker.

Run one outbox worker per `FOLDMIND_OUTBOX_PROJECTION_TARGET`.

Supported targets:

- `qdrant-document-chunks`
- `qdrant-documents`
- `qdrant-signals`
- `qdrant-folders`
- `neo4j-graph`

Each worker derives a target-specific consumer group name. That lets every
projection target consume the same outbox stream independently.

The default outbox topic is `indexing-events`. Configure Debezium so the Kafka
message key is the generated `partition_key` column.

Failed messages are published to `indexing-events.dlq`. After fixing the
underlying failure, replay them with `scripts/replay_dead_letter_events.py`.

For local workflow bootstrap without a separate checkpoint DSN, set
`FOLDMIND_ALLOW_IN_MEMORY_WORKFLOW_CHECKPOINT=true`. The standard configured API
still requires `FOLDMIND_POSTGRES_DSN`, `FOLDMIND_QDRANT_URL`, and graph DB settings.

## Current Limitations

- Dockerfile and Compose manifests are not present yet.
