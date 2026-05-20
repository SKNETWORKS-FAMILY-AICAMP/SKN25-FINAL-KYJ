# FoldMind-AI-Core

[English README](README.md)

FoldMind-AI-Core는 FoldMind 앱 서버 옆에서 동작하는 AI 처리 서버입니다.
앱 서버는 원본 문서, 폴더, 원본 태그, 권한, 사용자, 비즈니스 규칙을 계속 소유합니다.
AI-Core는 앱 서버가 보낸 현재 상태 복사본(snapshot)을 받아 검색용 데이터, 문서 AI
요약 정보, 가벼운 폴더 metadata 인덱스, 그래프 관계, 워크플로우 상태 같은 파생
데이터만 만듭니다.

AI-Core는 앱 서버 DB를 대체하지 않습니다. 원본 데이터를 저장하거나 직접 수정하지
않고, AI 처리에 필요한 파생 상태만 저장합니다.

## 한눈에 보기

| 영역 | 하는 일 |
| --- | --- |
| 문서 인덱싱 | 문서 본문을 작은 조각(chunk)으로 나누고, 각 조각의 embedding을 만들고, 문서 AI 프로필과 graph DB 관계를 저장합니다. |
| 폴더 인덱싱 | 폴더 metadata를 embedding하고, 가벼운 폴더 vector와 graph hierarchy 관계를 저장합니다. |
| 문서 검색 | 질문을 embedding으로 바꾼 뒤 vector DB와 graph DB를 함께 사용해 근거가 될 문서 조각을 찾습니다. |
| 답변 생성 | 검색된 문서 조각을 LLM에 전달하고, 답변과 근거를 반환합니다. |
| 워크플로우 | 자연어 요청을 실행 단계로 나누고, AI 작업을 실행하고, 원본 데이터 변경은 앱 서버가 실행할 action으로 제안합니다. |
| 저장 범위 | 원본 데이터가 아니라 문서 profile, vector payload, graph 관계, task snapshot, task event 같은 파생 데이터만 저장합니다. |

## 책임 경계

| 소유자 | 소유 대상 |
| --- | --- |
| FoldMind 앱 서버 | 원본 문서, 원본 폴더, 원본 태그, 권한, 사용자, 비즈니스 규칙 |
| AI-Core | 문서 AI 프로필, vector index payload, graph DB 관계, 검색 결과, 생성 결과, workflow 상태, 제안된 host action |

AI-Core는 앱 서버를 직접 호출하지 않습니다. 폴더 생성, 문서 이동처럼 원본 데이터를
바꾸는 작업은 AI-Core가 직접 실행하지 않고 `HostAction`으로 반환합니다. 앱 서버가
그 action을 승인, 실행, 거절, 수정하고 실행 결과를 AI-Core에 다시 보냅니다.

## 주요 기능

**문서 인덱싱**

앱 서버가 `SourceDocument` snapshot을 보냅니다. AI-Core는 본문을 검색하기 쉬운
문서 조각(`DocumentChunk`)으로 나누고 각 조각의 embedding을 만듭니다. 이어서 LLM이
profiling manifest(`DocumentProfile`)와 summary, concept, entity, issue,
commitment, claim 근거를 담은 `KnowledgeSignal`을 생성합니다.

인덱싱 요청은 PostgreSQL에 프로필과 outbox event를 원자적으로 저장합니다.
Qdrant/Graph DB projection은 Debezium Kafka consumer가 비동기로 만듭니다. Qdrant에는
chunk, signal, folder, 문서 단위 vector가 저장됩니다. Graph DB에는 문서-폴더,
문서-signal, 폴더-signal, 폴더 계층 관계가 저장됩니다. Neo4j projection
상태는 PostgreSQL에 ledger로 중복 저장하지 않고, outbox replay와 Kafka dead-letter
처리로 복구합니다. Chunk 본문은 Qdrant에 저장하고 graph DB에는 chunk node를 만들지
않습니다.

**폴더 인덱싱**

앱 서버가 `SourceFolder` snapshot을 보냅니다. AI-Core는 폴더 metadata와 그 폴더에
대한 name, path, description을 Qdrant folder collection에 embedding하고, graph DB에는
`Folder` node와 폴더 계층 관계를 저장합니다.

폴더 인덱싱은 PostgreSQL folder profile을 만들거나 저장하지 않습니다. 폴더 표시명,
path, description, hierarchy는 다시 만들 수 있는 검색용 파생 인덱스이며, 원본 표시
정보와 권한의 기준은 앱 서버입니다.

**문서 검색**

문서 검색은 두 종류의 저장소를 함께 사용합니다.

1. Qdrant는 질문과 의미가 비슷한 문서 조각과 문서를 vector similarity로 찾습니다.
2. Graph DB는 같은 폴더와 knowledge signal로 연결된 문서를 찾습니다.
3. AI-Core는 두 결과에서 문서 ID를 모으고, 그 문서들 안에서 다시 관련 chunk를 찾습니다.
4. 검색된 chunk를 점수순으로 정렬하고, relevance filter agent가 질문과 무관한
   chunk를 걸러냅니다.

`/retrieval/search`는 이 과정을 거쳐 문서 조각 목록을 반환합니다.

**질문 답변**

`/retrieval/answer`는 먼저 문서 검색을 실행합니다. 그 다음 검색된 chunk의 본문,
문서 ID, chunk ID, 점수를 LLM에 전달할 context로 포맷합니다. LLM은 이 context만
근거로 답변을 작성합니다. 응답에는 생성된 답변과 근거가 함께 들어갑니다. 이 근거는
API 응답의 `citations` 필드에 담깁니다.

**추천**

`/retrieval/folder-recommendations`는 앱 서버가 보낸 문서 snapshot을 기준으로 가장
알맞은 `folder_id`, score, reason을 반환합니다. 앱 서버는 반환된 `folder_id`로 표시
정보를 보강하고 문서를 어느 폴더에 넣을지 결정합니다.

**워크플로우**

`/tasks`는 자연어 요청을 받습니다. AI-Core는 요청을 검색, 추천, 요약, 답변, 초안 작성,
아이디어 생성, host action 계획 같은 실행 단계로 나눕니다. AI 단계는 AI-Core가 직접
실행합니다. 원본 데이터를 바꾸는 단계는 `HostAction`으로 반환하고 앱 서버의 실행
결과를 기다립니다.

## 앱 서버의 대표 호출 흐름

### 1. 문서 인덱싱

| 단계 | 일어나는 일 |
| --- | --- |
| 앱 서버가 보냄 | `POST /indexing/documents`에 문서 제목, 본문, 버전, 폴더 ID, metadata를 보냅니다. |
| AI-Core가 검증 | tenant, 원본 식별자, 버전, 검색 가능한 본문이 있는지 확인합니다. |
| AI-Core가 chunk 생성 | 본문을 일정 길이의 `DocumentChunk` 목록으로 나눕니다. |
| AI-Core가 embedding 생성 | 각 chunk 본문을 vector로 변환합니다. |
| AI-Core가 signal 생성 | LLM으로 profiling manifest와 summary, concept, entity, issue, commitment, claim signal을 생성합니다. |
| AI-Core가 저장 | PostgreSQL, Qdrant, graph DB에 파생 데이터를 저장합니다. |
| 앱 서버가 받음 | 생성된 chunk 개수를 받습니다. 원본 문서 소유권은 앱 서버에 그대로 남습니다. |

### 2. 질문 답변

| 단계 | 일어나는 일 |
| --- | --- |
| 앱 서버가 보냄 | `POST /retrieval/answer`에 질문, tenant, 검색 범위를 보냅니다. |
| AI-Core가 문서 ID 검색 | Qdrant의 문서 vector와 graph DB 관계 검색으로 관련 문서 ID를 찾습니다. |
| AI-Core가 chunk 검색 | 관련 문서 안에서 질문과 가장 가까운 chunk를 찾습니다. 관련 문서 ID가 없으면 요청된 검색 범위 안에서 바로 chunk를 찾습니다. |
| AI-Core가 chunk 필터링 | relevance filter agent가 질문과 무관한 chunk를 제거합니다. |
| AI-Core가 답변 생성 | answer generation agent가 남은 chunk를 근거로 답변을 작성합니다. |
| 앱 서버가 받음 | 답변 text와 근거를 받습니다. |

### 3. 워크플로우 task 실행

| 단계 | 일어나는 일 |
| --- | --- |
| 앱 서버가 시작 | `POST /tasks`에 tenant와 자연어 요청을 보냅니다. task ID와 task request ID는 AI-Core가 생성합니다. |
| 앱 서버가 이어쓰기 | 기존 `task_id`를 넣어 `POST /tasks`를 호출하면 새 task를 만들지 않고 같은 task에 요청을 추가합니다. |
| AI-Core가 계획 | planning agent가 자연어 요청을 실행 가능한 workflow step 목록으로 바꿉니다. |
| AI-Core가 실행 | 검색, 추천, 요약, 답변, 초안 작성, 아이디어 생성 step을 실행합니다. |
| AI-Core가 action 제안 | 원본 데이터를 바꾸는 step은 앱 서버가 실행할 `HostAction`으로 task snapshot에 담습니다. |
| 앱 서버가 처리 | 앱 서버가 action을 승인, 실행, 거절, 수정, skip, retry 중 하나로 처리합니다. |
| 앱 서버가 보고 | `POST /tasks/actions/result`로 처리 결과를 AI-Core에 보냅니다. |
| AI-Core가 재개 | 저장된 checkpoint에서 workflow를 이어 실행하고 최신 task snapshot을 반환합니다. |

## REST API

모든 REST DTO는 알 수 없는 field를 거부합니다. 입력 검증 오류는 `422`로 반환됩니다.
task나 recommendation target을 찾지 못한 경우 해당 route는 `404`를 반환합니다.

### System

| Method | Path | 목적 |
| --- | --- | --- |
| `GET` | `/health` | process가 살아 있는지 확인합니다. 정상 응답은 `{"status": "ok"}`입니다. |

### Indexing

| Method | Path | Request DTO | Response DTO | 목적 |
| --- | --- | --- | --- | --- |
| `POST` | `/indexing/documents` | `IndexDocumentRequest` | `IndexDocumentResponse` | 문서 snapshot을 인덱싱하고 생성된 chunk 개수를 반환합니다. |
| `DELETE` | `/indexing/documents/{document_id}` | - | `204 No Content` | 해당 문서의 profile, vector payload, graph DB 관계를 삭제합니다. |
| `POST` | `/indexing/folders` | `IndexFolderRequest` | `IndexFolderResponse` | 폴더 snapshot을 인덱싱하고 검색용 folder 모델을 반환합니다. |
| `DELETE` | `/indexing/folders/{folder_id}` | - | `204 No Content` | 해당 폴더의 vector payload와 graph DB 관계를 삭제합니다. |

### Retrieval And Recommendations

| Method | Path | Request DTO | Response DTO | 목적 |
| --- | --- | --- | --- | --- |
| `POST` | `/retrieval/search` | `SearchDocumentsRequest` | `SearchDocumentsResponse` | 질문과 관련된 AI-Core 인덱싱 문서 조각을 반환합니다. |
| `POST` | `/retrieval/answer` | `AnswerQuestionRequest` | `GeneratedTextResponse` | 관련 chunk를 찾고, 그 chunk를 근거로 답변을 생성한 뒤 답변과 근거를 반환합니다. |
| `POST` | `/retrieval/folder-recommendations` | `RecommendFolderRequest` | `RecommendFolderResponse` | 문서 snapshot에 가장 알맞은 `folder_id`를 추천합니다. |

### Workflow Tasks

| Method | Path | Request DTO | Response DTO | 목적 |
| --- | --- | --- | --- | --- |
| `POST` | `/tasks` | `CreateTaskRequest` | `TaskSnapshotResponse` | task를 시작하거나 기존 task에 요청을 추가합니다. |
| `GET` | `/tasks/{task_id}` | - | `TaskSnapshotResponse` | 앱 서버가 볼 수 있는 최신 task snapshot을 조회합니다. |
| `DELETE` | `/tasks/requests/{task_request_id}` | - | `TaskSnapshotResponse` | task 안의 요청 entry를 removed로 표시하고 남은 active 요청으로 다시 계획합니다. |
| `POST` | `/tasks/actions/result` | `RecordHostActionResultRequest` | `RecordHostActionResultResponse` | 앱 서버가 host action 처리 결과를 보낸 뒤 중단된 workflow를 재개합니다. |

## 검색 동작

문서 검색은 `FindDocumentsUseCase`가 실행합니다.

1. 질문 text를 embedding으로 변환합니다.
2. Qdrant `documents` collection에서 질문과 가까운 문서 ID를 찾습니다.
3. Graph DB에서 질문 text와 연결된 폴더와 knowledge signal을 통해 관련 문서 ID를 찾습니다.
4. 2번과 3번에서 문서 ID가 나오면 그 문서들 안에서 chunk vector 검색을 실행합니다.
5. 문서 ID가 나오지 않으면 요청의 `SearchScope`만 적용해 chunk vector 검색을 실행합니다.
6. `ChunkRelevanceFilterAgent`가 질문과 관련 없는 chunk를 제거합니다.

현재 Qdrant adapter는 dense chunk vector, document-level vector, folder vector를
구현합니다.

## 워크플로우 생명주기

워크플로우 API는 AI-Core가 추론과 제안을 맡고, 앱 서버가 원본 데이터 변경을 통제하는
구조입니다.

1. 앱 서버가 `POST /tasks`에 tenant와 자연어 요청을 보냅니다. AI-Core가 `task_id`와 `task_request_id`를 생성합니다.
2. 이후 같은 `task_id`로 `POST /tasks`를 호출하면 새 task가 아니라 기존 task에 요청을 추가합니다.
3. `RunTaskUseCase`가 현재 `TaskSnapshot`을 저장하고 workflow runtime을 호출합니다.
4. `PlanningAgent`가 active 요청들을 `WorkflowPlan`으로 바꿉니다.
5. `WorkflowPlanCompiler`가 plan을 실행 가능한 step 목록으로 바꿉니다.
6. `WorkflowStepExecutor`가 각 step을 검색, 추천, 생성, host-action planning step로 보냅니다.
7. step 결과는 `WorkflowArtifactRegistry`를 통해 기록되고, 앱 서버가 볼 수 있는 `TaskOutput`으로 노출됩니다.
8. 앱 서버는 `DELETE /tasks/requests/{task_request_id}`로 특정 요청 entry를 removed 처리할 수 있습니다.
9. 앱 서버가 `POST /tasks/actions/result`로 action 처리 결과를 보내면 workflow가 checkpoint에서 재개됩니다.
10. 남은 step과 pending action이 없으면 최종 `TaskSnapshot`이 저장됩니다.

## Agents

Agent는 하나의 prompt-backed LLM 작업을 담당하는 application-layer component입니다.
agent는 OpenAI SDK에 직접 의존하지 않고 `LLMProvider`와 `PromptStore`에
의존합니다.

| Agent | Prompt key | 사용 위치 | 책임 |
| --- | --- | --- | --- |
| `PlanningAgent` | `workflow_planning` | `WorkflowEngine.prepare()` | 자연어 task를 검증된 `WorkflowPlan`으로 바꿉니다. |
| `DocumentProfilerAgent` | `document_profiling` | `IndexDocumentUseCase` | 문서와 chunk를 분석해 `DocumentProfile` manifest와 `KnowledgeSignal` 집합을 생성합니다. |
| `ChunkRelevanceFilterAgent` | `chunk_relevance_filtering` | `FindDocumentsUseCase` | 검색된 chunk 중 질문과 관련 있는 chunk만 남깁니다. |
| `ContextGenerationAgent` | `answer_generation`, `summarization`, `draft_generation`, `ideas_exploration` | retrieval과 workflow generation step | 호출자가 고른 prompt로 검색된 chunk를 근거로 cited text를 생성합니다. |

Context generation agent는 검색된 chunk를 LLM에 전달하기 전에
`UNTRUSTED_CONTEXT_INSTRUCTION`을 prompt에 넣습니다. planner는
`ALLOWED_WORKFLOW_ACTION_TYPES`를 prompt에 넣어 runtime이 지원하는 action만 선택하게
합니다.

## 도메인 모델

| 영역 | 주요 모델 | 의미 |
| --- | --- | --- |
| Source snapshot | `SourceDocument`, `SourceFolder` | 앱 서버가 보낸 원본 데이터의 현재 상태 복사본입니다. AI-Core로 소유권이 넘어오지 않습니다. |
| Retrieval/index model | `DocumentChunk`, `DocumentVectorProjection`, `FolderVectorProjection`, `RetrievedDocument`, `RetrievedFolder` | AI-Core가 만든 저장소별 projection과 retrieval-facing reference입니다. |
| AI profile | `DocumentProfile`, `KnowledgeSignal` | profiling 실행 manifest와 signalized summary, concept, entity, issue, commitment, claim 결과입니다. |
| Retrieval | `RetrievalQuery`, `RequestContext`, `SearchScope`, `QueryAnchor` | 질문 text, tenant 정보, 검색 범위, anchor입니다. |
| Generation | `GeneratedTextResult`, `DraftResult`, recommendation result, clarification result | 생성/추천 step의 typed output입니다. |
| Workflow | `TaskRequest`, `TaskSnapshot`, `TaskAnalysis`, `TaskOutput`, `TaskEvent` | 앱 서버가 조회하는 task 상태와 output입니다. |
| Host action | `HostAction`, `HostActionResult`, action input/output payload | 앱 서버가 실행해야 하는 제안된 원본 데이터 변경입니다. |
| Knowledge graph | `DocumentRelationshipProjection`, `DocumentSignalGraphProjection`, `FolderRelationshipProjection` | 문서, 폴더, knowledge signal 사이의 파생 관계입니다. |
| Outbox event | `OutboxEvent` | PostgreSQL profile 변경과 같은 transaction에서 발행되는 projection 입력 event입니다. |

중요한 규칙:

- source model은 snapshot입니다. 원본 데이터의 기준은 앱 서버입니다.
- indexed model과 AI profile은 다시 만들 수 있는 파생 상태입니다.
- task output은 type이 정해져 있습니다. 예를 들어 `summary` output은 generated text를 담아야 합니다.
- host action payload는 `HostActionType`과 맞아야 합니다.
- DTO가 API 입력을 검증한 뒤 mapper가 use case command/query를 만듭니다.

## 데이터 저장

AI-Core는 AI 파생 상태만 저장합니다. 원본 문서, 원본 폴더, 원본 태그, 권한은 저장하지
않습니다. 원본 태그가 필요하면 source metadata의 opaque 값으로만 전달하며, AI-Core는
이를 graph 관계나 검색 scope로 승격하지 않습니다.

### PostgreSQL

| Table | Primary Key | 저장 내용 |
| --- | --- | --- |
| `tenant_storage_scopes` | `tenant_id` | tenant 단위 AI-Core 저장 범위와 retention 상태 |
| `document_refs`, `folder_refs` | UUID refs | source identity. `document_id`, `folder_id`는 App Server의 canonical key이고 `document_type`은 설명용 metadata |
| `source_document_snapshots`, `source_folder_snapshots` | UUID snapshots | 최소 snapshot manifest: source identity, digest, size, schema version, metadata, timestamp. 원문 body와 storage 위치는 저장하지 않음 |
| `document_index_records`, `document_chunk_sets`, `document_chunks`, `folder_index_records` | UUID records | 현재/이전 파생 index manifest와 chunk record |
| `knowledge_signals` | `signal_id` | 추출된 signal text, payload, evidence, confidence, extractor metadata, source document/version scope |
| `vector_projection_records` | UUID projection IDs | Qdrant write ledger. Vector record는 source row FK 없이 collection, point ID, aggregate/subject identity, payload digest, projected/deleted timestamp, retention 상태를 기록 |
| `outbox_events` | `id` UUID | Kafka/Debezium transactional outbox event. `tenant_id`, `idempotency_key`, `sequence`, `event_key`로 stream ordering, idempotency, dead-letter context 제공 |
| `retrieval_runs`, `retrieval_results` | UUID run/result IDs | 사용자-facing retrieval 요청 기록. query 원문은 저장하지 않고 digest, scope, status, result id, score, reason만 저장 |
| `tasks` | `task_id` UUID | 현재 task aggregate status, active request text, analysis message, current action, error, metadata |
| `task_requests` | `task_request_id` UUID | task 안에 쌓인 사용자 요청 entry와 active/removed 상태 |
| `task_outputs` | `output_id` UUID | typed task output, result payload, task-local ordering |
| `host_actions` | `action_id` UUID | 제안된 host action, typed input payload, result payload, policy JSON, task-local 순차 ordering |
| `task_events` | `event_id` UUID | task event log |

PostgreSQL schema는 Alembic으로 관리합니다. API를 시작하기 전에 migration을 실행합니다.

```bash
FOLDMIND_POSTGRES_DSN=postgresql://user:password@host:5432/foldmind_ai_core alembic upgrade head
```

초기 migration chain은 최적화된 최초 버전의 파생 상태 schema, Kafka outbox,
Qdrant vector ledger, workflow task table을 생성합니다.

### Qdrant

| Setting | 기본 Collection | Payload Kind | 목적 |
| --- | --- | --- | --- |
| `FOLDMIND_QDRANT_DOCUMENT_CHUNK_COLLECTION` | `document_chunks` | `document_chunk` | chunk 본문에 대한 vector search |
| `FOLDMIND_QDRANT_DOCUMENT_COLLECTION` | `documents` | `document` | 문서 프로필을 포함한 문서 단위 vector search |
| `FOLDMIND_QDRANT_SIGNAL_COLLECTION` | `signals` | `signal` | 추출된 knowledge signal에 대한 signal 단위 vector search |
| `FOLDMIND_QDRANT_FOLDER_COLLECTION` | `folders` | `folder` | 폴더 discovery와 추천을 위한 folder metadata vector search |

### Graph DB

Graph DB는 표준 AI-Core API의 필수 저장소입니다. 문서 인덱싱과 폴더 인덱싱은 항상
graph DB에 관계를 기록합니다.

| 관계 | 의미 |
| --- | --- |
| `Document` - `Folder` | 문서가 어떤 폴더에 속하는지 |
| `Document` - `Signal` | 문서 버전에 어떤 추출된 knowledge signal이 연결되는지 |
| `Folder` - `Folder` | 폴더 계층 관계 |

Graph DB의 관계는 검색 품질을 높이기 위한 파생 데이터입니다. 원본 폴더 구조, 권한,
태그의 기준 데이터는 앱 서버에 있습니다.

### Workflow Checkpoints

production workflow checkpoint는 `FOLDMIND_WORKFLOW_CHECKPOINT_DSN` 또는
`FOLDMIND_POSTGRES_DSN`을 통해 PostgreSQL에 저장합니다. in-memory checkpointer는 local/test
설정에서만 사용합니다.

## 아키텍처

AI-Core는 hexagonal architecture를 따릅니다. application layer는 interface(port)에
의존하고, FastAPI, PostgreSQL, Qdrant, graph DB, OpenAI SDK, LangGraph 같은 구체 기술은
adapter layer에 둡니다.

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

| Package | 역할 |
| --- | --- |
| `core/domain/models/` | business model입니다. 외부 framework에 의존하지 않습니다. |
| `core/domain/services/` | concept normalization, confidence validation, outbox invariant 같은 순수 domain rule입니다. |
| `core/application/ports/inbound/` | 앱 서버가 호출하는 use case contract입니다. |
| `core/application/ports/outbound/` | LLM provider, embedding provider, PostgreSQL repository, vector store, graph store, prompt store, workflow runtime interface입니다. |
| `core/application/use_cases/` | indexing, retrieval, recommendation, workflow task orchestration입니다. |
| `core/application/agents/` | prompt-backed AI 작업입니다. |
| `core/application/workflows/` | workflow step 실행, artifact 저장, host action 처리 정책입니다. |
| `adapters/inbound/http/` | FastAPI router, REST DTO, HTTP error mapping입니다. |
| `adapters/outbound/` | PostgreSQL, Qdrant, graph DB, OpenAI, LangGraph, file prompt store 구현입니다. |
| `bootstrap/` | 설정을 읽고 concrete adapter를 use case에 연결합니다. |

## 배포와 설정

이 repository는 endpoint 기반 설정을 사용합니다. 전역 `DB_MODE=local/cloud` 값은
없습니다. PostgreSQL, Qdrant, graph DB endpoint를 각각 설정합니다.
Dockerfile과 Compose manifest는 아직 없습니다.

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
`FOLDMIND_DOCUMENT_PROFILE_PROMPT_VERSION`은 표준 configured API에서 필수입니다.

예시 환경 파일:

- `examples/env/local.env`: local self-hosted endpoint 예시입니다.
- `examples/env/local-postgres-external-services.env`: local PostgreSQL과 외부
  Qdrant, graph DB, Kafka endpoint 조합 예시입니다.
- `examples/env/external.env`: 외부 PostgreSQL, Qdrant, graph DB endpoint 예시입니다.

## 패키지 구조

```text
foldmind-ai-core/
  scripts/         로컬 실행 및 운영 entrypoint
  src/foldmind_ai_core/
    main.py        설정 기반 ASGI process entrypoint
    resources/     runtime package data와 bundled prompt
    bootstrap/     설정, app factory, container wiring
    core/
      domain/        domain model과 순수 domain service
      application/   use case, port, agent, workflow policy
    adapters/      inbound/outbound concrete adapter
    shared/        공유 primitive type과 validation rule
  tests/
    unit/          활성 unit test
    contract/      활성 app-server/schema contract test
```

패키지 이름은 `foldmind_ai_core`입니다.

## 개발

```bash
python -m pip install -r requirements.txt
PYTHONPATH=src python -S -c "import foldmind_ai_core.core.domain; import foldmind_ai_core.core.application.ports"
PYTHONPATH=src python -m unittest discover -s tests
PYTHONPATH=src python -m compileall -q src tests
python -m pip install -e ".[dev]"
ruff check src tests
mypy src
```

`scripts/run_api.sh`는 configured ASGI app을 실행합니다. `scripts/run_worker.sh`는
Kafka outbox projection worker를 실행합니다.

outbox worker는 `FOLDMIND_OUTBOX_PROJECTION_TARGET`별로 하나씩 실행합니다:
`qdrant-document-chunks`, `qdrant-documents`, `qdrant-signals`,
`qdrant-folders`, `neo4j-graph`.
worker는 항상 target별 consumer group 이름을 자동으로 만들기 때문에 각 projection
target이 같은 outbox stream을 독립적으로 consume합니다.

별도 checkpoint DSN 없이 local workflow bootstrap을 하려면
`FOLDMIND_ALLOW_IN_MEMORY_WORKFLOW_CHECKPOINT=true`를 설정합니다. 표준 configured API는
그래도 `FOLDMIND_POSTGRES_DSN`, `FOLDMIND_QDRANT_URL`, graph DB 설정을 요구합니다.

## 현재 한계

- Dockerfile과 Compose manifest가 아직 없습니다.
