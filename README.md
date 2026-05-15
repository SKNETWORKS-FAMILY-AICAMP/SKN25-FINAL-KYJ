# FoldMind-AI-Core

[한국어 README](README.ko.md)

FoldMind-AI-Core is the AI processing server that runs beside the FoldMind app
server. The app server remains the owner of source documents, folders, tags,
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
| FoldMind app server | Source documents, source folders, tags, permissions, users, and business rules. |
| AI-Core | Document AI profiles, vector index payloads, graph DB relationships, retrieval results, generated outputs, workflow state, and proposed host actions. |

AI-Core does not call the app server directly. When a task needs to create a folder,
move a document, or perform another source-data change, AI-Core returns a
`HostAction`. The app server approves, executes, rejects, or modifies that action
and reports the result back to AI-Core.

## Main Capabilities

**Document Indexing**

The app server sends a `SourceDocument` snapshot. AI-Core splits the body into
searchable `DocumentChunk` records and creates an embedding for each chunk. The LLM
then creates a document AI profile (`DocumentProfile`) containing the source title,
summary, derived concepts, profile confidence, model name, and prompt version.

Indexing writes the profile and an outbox event atomically to PostgreSQL.
Debezium Kafka consumers asynchronously project Qdrant and graph DB state. Outbox
events carry a database-generated sequence and an `AGGREGATE:ID` event key so
workers can skip stale messages. Qdrant stores chunk vectors and document-level vectors. The graph DB stores
document-to-folder, document-to-tag, document-to-concept, tag-to-concept, and folder
hierarchy relationships. Chunk text stays in Qdrant; chunk nodes are not projected
into the graph DB.

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
2. The graph DB finds documents linked through folders, tags, and derived concepts.
3. AI-Core combines the document IDs found by both stores and searches chunks inside those documents.
4. Retrieved chunks are ranked by score.
5. The relevance validation agent removes chunks that do not answer the question.

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
| App server sends | `POST /indexing/documents` with title, body, version, folder IDs, tags, and metadata. |
| AI-Core validates | Tenant, source identity, version, and indexable text are checked. |
| AI-Core creates chunks | The body is split into `DocumentChunk` records. |
| AI-Core creates embeddings | Each chunk body is converted into a vector. |
| AI-Core creates a profile | The LLM generates title-backed summary, derived concepts, and profile confidence. |
| AI-Core stores derived data | PostgreSQL, Qdrant, and the graph DB receive derived records. |
| App server receives | The indexed chunk count. The source document remains owned by the app server. |

### 2. Answer A Question

| Step | What Happens |
| --- | --- |
| App server sends | `POST /retrieval/answer` with question, tenant, and search scope. |
| AI-Core finds document IDs | Qdrant document vectors and graph DB relationship search find related document IDs. |
| AI-Core finds chunks | Chunks are searched inside those documents. If no document IDs are found, chunk search runs directly within the requested scope. |
| AI-Core validates chunks | The relevance validation agent removes chunks unrelated to the question. |
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
| `POST` | `/indexing/documents/delete` | `DeleteDocumentIndexRequest` | `DeleteDocumentIndexResponse` | Delete the document profile, vector payloads, and graph DB relationships. |
| `POST` | `/indexing/folders` | `IndexFolderRequest` | `IndexFolderResponse` | Index a folder snapshot and return the searchable folder model. |
| `POST` | `/indexing/folders/delete` | `DeleteFolderIndexRequest` | `DeleteFolderIndexResponse` | Delete the folder vector payloads and graph DB relationships. |

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
| `GET` | `/tasks/{tenant}/{task_id}` | - | `TaskSnapshotResponse` | Read the latest task snapshot visible to the app server. |
| `DELETE` | `/tasks/{tenant}/{task_id}/requests/{task_request_id}` | - | `TaskSnapshotResponse` | Mark a request entry as removed and replan from the active requests. |
| `POST` | `/tasks/actions/result` | `RecordHostActionResultRequest` | `RecordHostActionResultResponse` | Resume a paused workflow after the app server reports a host action result. |

## Search Behavior

Document search is implemented by `FindDocumentsUseCase`.

1. Convert the question text into an embedding.
2. Search the Qdrant `documents` collection for related document IDs.
3. Search the graph DB for document IDs connected to the question through tags, folders, and derived concepts.
4. If document IDs were found, run chunk vector search inside those documents.
5. If no document IDs were found, run chunk vector search directly within the request `SearchScope`.
6. If an optional keyword repository is configured and the mode is `hybrid`, combine dense and keyword results with reciprocal rank fusion.
7. `ChunkRelevanceValidatorAgent` removes chunks that are not related to the question.

The current Qdrant adapter implements dense chunk vectors, document-level vectors,
and folder vectors. Keyword search is split into the optional
`DocumentKeywordRepository`; the current Qdrant adapter does not implement keyword
indexing.

## Workflow Lifecycle

The workflow API lets AI-Core reason and propose actions while the app server keeps
control of source-data changes.

1. The app server calls `POST /tasks` with tenant and a natural-language request. AI-Core generates `task_id` and `task_request_id`.
2. A later `POST /tasks` with the same `task_id` appends another request to the same task instead of creating a new task.
3. `RunTaskUseCase` stores the current `TaskSnapshot` and calls the workflow runtime.
3. `PlanningAgent` turns the request into a `WorkflowPlan`.
4. `WorkflowPlanCompiler` turns the plan into executable steps.
5. `WorkflowStepExecutor` dispatches each step to a search, recommendation, generation, or host-action planning handler.
6. Step results are stored in `WorkflowArtifactStore` and exposed as app-server-visible `TaskOutput` values.
7. When a host action is created, the workflow saves a checkpoint and pauses.
8. The app server can remove a request entry through `DELETE /tasks/{tenant}/{task_id}/requests/{task_request_id}`.
9. The app server reports the action result through `POST /tasks/actions/result`, and the workflow resumes from the checkpoint.
10. When no steps or pending actions remain, the final `TaskSnapshot` is stored.

## Agents

An agent is an application-layer component responsible for one prompt-backed LLM
task. Agents depend on `LLM` and `PromptRepositoryPort`, not directly on the OpenAI
SDK.

| Agent | Prompt key | Used by | Responsibility |
| --- | --- | --- | --- |
| `PlanningAgent` | `workflow_planning` | `WorkflowEngine.prepare()` | Turn a natural-language task into a validated `WorkflowPlan`. |
| `DocumentProfilerAgent` | `document_profiling` | `IndexDocumentUseCase` | Create a `DocumentProfile` from a document and its chunks. |
| `ChunkRelevanceValidatorAgent` | `chunk_relevance_validation` | `FindDocumentsUseCase` | Keep only retrieved chunks related to the question. |
| `AnswerGeneratorAgent` | `answer_generation` | `AnswerQuestionUseCase`, workflow `answer_question` step | Generate a cited answer from retrieved chunks. |
| `SummarizerAgent` | `summarization` | Workflow summary/report steps | Generate a summary from retrieved chunks. |
| `DraftGeneratorAgent` | `draft_generation` | Workflow `generate_draft` step | Generate a draft from user instructions and retrieved context. |
| `IdeasExplorerAgent` | `ideas_exploration` | Workflow `explore_ideas` step | Generate ideas from a user prompt and retrieved context. |

RAG-oriented agents render `UNTRUSTED_CONTEXT_INSTRUCTION` into prompts before
passing retrieved chunks to the LLM. The planner renders
`ALLOWED_WORKFLOW_ACTION_TYPES` so the model selects only actions supported by the
runtime.

## Domain Model

| Area | Key Models | Meaning |
| --- | --- | --- |
| Source snapshot | `SourceDocument`, `SourceFolder` | Current-state source data sent by the app server. Ownership does not transfer to AI-Core. |
| Retrieval/index model | `DocumentChunk`, `DocumentVectorProjection`, `FolderVectorProjection`, `RetrievedDocument`, `RetrievedFolder` | Store-specific projections and retrieval-facing references created by AI-Core. |
| AI profile | `DocumentProfile` | AI-generated document title snapshot, summary, derived concepts, and profile confidence. |
| Retrieval | `AIQuery`, `RequestContext`, `SearchScope`, `QueryAnchor` | Question text, tenant information, search scope, and anchor. |
| Generation | `GeneratedTextResult`, `DraftResult`, recommendation results, clarification results | Typed outputs produced by generation and recommendation steps. |
| Workflow | `TaskRequest`, `TaskSnapshot`, `TaskAnalysis`, `TaskOutput`, `TaskEvent` | Task state and outputs visible to the app server. |
| Host action | `HostAction`, `HostActionResult`, action input/output payload | Proposed source-data change that the app server must execute. |
| Knowledge graph | `DocumentRelationshipProjection`, `DocumentConceptProjection`, `FolderRelationshipProjection`, `TagProjection` | Derived relationships between documents, folders, tags, and concepts. |
| Outbox event | `OutboxEvent` | Immutable projection input event emitted with PostgreSQL profile changes. |

Important rules:

- Source models are snapshots. The app server remains canonical.
- Vector projections and AI profiles are rebuildable derived state.
- Task outputs are typed. For example, a `summary` output must contain generated text.
- Host action payloads must match `HostActionType`.
- DTOs validate API input before mapping into plain domain state containers.

## Data Storage

AI-Core stores derived AI state only. It does not store canonical documents,
canonical folders, canonical tags, or permissions.

### PostgreSQL

| Table | Primary Key | Stores |
| --- | --- | --- |
| `document_profiles` | `document_id` | Latest document profile title, summary, concepts JSON, profile confidence, source/profile/schema versions, and metadata. |
| `outbox_events` | `id` UUID | Transactional outbox events consumed through Debezium Kafka to project Qdrant and graph DB state. `sequence` and `event_key` are used for ordering and stale-message protection. |
| `tasks` | `task_id` UUID | Current task aggregate status, active request text, analysis message, current action, error, and metadata. |
| `task_requests` | `task_request_id` UUID | Ordered user request entries within a task, including active/removed status. |
| `task_outputs` | `output_id` UUID | Typed task outputs with result payloads and task-local ordering. |
| `host_actions` | `action_id` UUID | Proposed host actions with typed input payloads, result payloads, policy JSON, and task-local ordering. |
| `host_action_dependencies` | `action_id` + `depends_on_action_id` | Host action dependency edges with FK validation. |
| `task_events` | `event_id` UUID | Task event log. |

PostgreSQL schema is managed by Alembic. Run migrations before starting the API:

```bash
POSTGRES_DSN=postgresql://user:password@host:5432/foldmind_ai_core alembic upgrade head
```

The initial migration chain creates normalized profile, outbox, and task tables for
a fresh database. It does not include conversion steps from an older storage
format.

### Qdrant

| Setting | Default Collection | Payload Kind | Purpose |
| --- | --- | --- | --- |
| `QDRANT_DOCUMENT_CHUNK_COLLECTION` | `document_chunks` | `document_chunk` | Vector search over chunk text. |
| `QDRANT_DOCUMENT_COLLECTION` | `documents` | `document` | Document-level vector search over profile-enriched text. |
| `QDRANT_FOLDER_COLLECTION` | `folders` | `folder` | Folder metadata vector search for folder discovery and recommendations. |

### Graph DB

The graph DB is required for the standard AI-Core API. Document indexing and folder
indexing always write relationships to the graph DB.

| Relationship | Meaning |
| --- | --- |
| `Document` - `Folder` | Which folders contain a document. |
| `Document` - `Tag` | Which tags are attached to a document. |
| `Document` - `Concept` | Which derived concepts appear in a document profile. |
| `Tag` - `Concept` | Which derived concept a tag represents. |
| `Folder` - `Folder` | Folder hierarchy. |

Graph DB relationships are derived data for retrieval quality. The app server
remains the source of truth for folder structure, permissions, and tags.

### Workflow Checkpoints

Production workflow checkpoints are stored in PostgreSQL through
`FOLDMIND_WORKFLOW_CHECKPOINT_DSN` or `POSTGRES_DSN`. The in-memory checkpointer is
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
  LLM / embeddings / vector index / graph DB / repositories / runtime
        |
        v
Outbound adapters
  OpenAI / PostgreSQL / Qdrant / graph DB / LangGraph / file prompts
```

| Package | Role |
| --- | --- |
| `domain/` | Business models and validation. No external framework dependencies. |
| `application/ports/inbound/` | Use case contracts called by the app server. |
| `application/ports/outbound/` | Interfaces for LLMs, embeddings, repositories, vector indexes, graph DB, prompts, and workflow runtime. |
| `application/use_cases/` | Indexing, retrieval, recommendation, and workflow task orchestration. |
| `application/agents/` | Prompt-backed AI tasks. |
| `application/workflows/` | Workflow step execution, artifact storage, and host action handling policy. |
| `adapters/inbound/http/` | FastAPI routers, REST DTOs, and HTTP error mapping. |
| `adapters/outbound/` | PostgreSQL, Qdrant, graph DB, OpenAI, LangGraph, and file prompt implementations. |
| `bootstrap/` | Read settings and wire concrete adapters into use cases. |

## Deployment And Configuration

This repository uses endpoint-based configuration. There is no global
`DB_MODE=local/cloud` setting. Configure PostgreSQL, Qdrant, and the graph DB with
their own endpoints. Dockerfile and Compose manifests are not present yet.

```dotenv
POSTGRES_DSN=postgresql://user:password@host:5432/foldmind_ai_core

AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4.1-mini
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_VERSION=text-embedding-3-small
CHUNKING_VERSION=chunking-v1
INDEX_SCHEMA_VERSION=index-schema-v1
PROFILE_VERSION=profile-v1
PROFILE_SCHEMA_VERSION=profile-schema-v1
DOCUMENT_PROFILE_PROMPT_VERSION=document-profile-prompt-v1
EMBEDDING_DIMENSIONS=1536

QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=

NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

`POSTGRES_DSN`, `QDRANT_URL`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`,
`EMBEDDING_VERSION`, `CHUNKING_VERSION`, `INDEX_SCHEMA_VERSION`,
`PROFILE_VERSION`, `PROFILE_SCHEMA_VERSION`, and
`DOCUMENT_PROFILE_PROMPT_VERSION` are required for the standard configured API.

Example environment files:

- `.env.example`: root template listing supported settings.
- `examples/env/local.env`: local self-hosted endpoint example.
- `examples/env/hybrid.env`: local PostgreSQL with external Qdrant and graph DB.
- `examples/env/external.env`: external PostgreSQL, Qdrant, and graph DB endpoints.

## Package Layout

```text
foldmind-ai-core/
  resources/
    prompts/       Prompt template source copies for local editing/reference
  scripts/         Local helper entrypoints
  src/foldmind_ai_core/
    main.py        Configured ASGI process entrypoint
    resources/     Runtime package data and bundled prompts
    bootstrap/     Settings, app factory, and container wiring
    domain/        Business models and validation
    application/   Use cases, ports, agents, and workflow policy
    adapters/      Inbound and outbound concrete adapters
    shared/        Shared primitive types and validation utilities
  tests/
    unit/          Active unit tests
    contract/      Active app-server and schema contract tests
    integration/   Placeholder package for future external-service tests
    e2e/           Placeholder package for future end-to-end flows
```

The package name is `foldmind_ai_core`. The previous `ai_core` package path has
been removed.

## Development

```bash
python -m pip install -r requirements.txt
PYTHONPATH=src python -S -c "import foldmind_ai_core.domain; import foldmind_ai_core.application.ports"
PYTHONPATH=src python -m unittest discover -s tests
PYTHONPATH=src python -m compileall -q src tests
python -m pip install -e ".[dev]"
ruff check src tests
mypy src
```

`scripts/run_api.sh` starts the configured ASGI app. `scripts/run_worker.sh`
starts the Kafka outbox projection worker. `scripts/reindex_documents.py` is a
placeholder until the standalone reindex entrypoint is wired.

Run one outbox worker per `OUTBOX_PROJECTION_TARGET`: `qdrant-document-chunks`,
`qdrant-documents`, `qdrant-folders`, or `neo4j-graph`. The worker always derives
a target-specific consumer group name so each projection target consumes the same
outbox stream independently.
The default outbox topic is `indexing-events`; configure Debezium so the Kafka
message key is the `event_key` column. Failed messages are published to
`indexing-events.dlq`; replay them with `scripts/replay_dlq.py` after fixing the
underlying failure.

For local workflow bootstrap without a separate checkpoint DSN, set
`FOLDMIND_ALLOW_IN_MEMORY_WORKFLOW_CHECKPOINT=true`. The standard configured API
still requires `POSTGRES_DSN`, `QDRANT_URL`, and graph DB settings.

## Current Limitations

- Dockerfile and Compose manifests are not present yet.
- The current Qdrant adapter does not implement keyword indexing.
- `tests/integration/` and `tests/e2e/` are placeholder packages.
- `scripts/reindex_documents.py` is a placeholder.
