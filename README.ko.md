# FoldMind-AI-Core

[English README](README.md)

FoldMind-AI-Core는 FoldMind 앱 서버 옆에서 동작하는 AI 처리 서버입니다.
앱 서버는 원본 문서, 폴더, 원본 태그, 권한, 사용자, 비즈니스 규칙을 계속 소유합니다.
AI-Core는 앱 서버가 보낸 현재 상태 복사본(snapshot)을 받아 가벼운 source manifest와
검색용 데이터, 문서 index record와 signal, 폴더 index record, 그래프 관계,
워크플로우 상태 같은 AI-Core 상태를 만듭니다.

AI-Core는 앱 서버 DB를 대체하지 않습니다. 원문 body를 저장하지 않고 canonical 원본
데이터를 직접 수정하지 않으며, AI 처리에 필요한 source manifest와 파생 상태만
저장합니다.

## 한눈에 보기

- **문서 인덱싱:** 문서 본문을 chunk로 나누고, index record와 signal을 만든 뒤
  vector/graph projection용 outbox event를 발행합니다.
- **폴더 인덱싱:** 가벼운 폴더 index 상태를 저장하고, folder vector와 hierarchy
  projection용 outbox event를 발행합니다.
- **문서 검색:** vector 검색, keyword 검색, graph 검색을 함께 사용해 근거 chunk를
  찾습니다.
- **답변 생성:** 검색된 chunk를 LLM에 전달하고 답변과 근거를 반환합니다.
- **워크플로우:** 자연어 요청을 실행 단계로 나누고, 원본 데이터 변경은 앱 서버가
  실행할 action으로 제안합니다.
- **저장 범위:** source manifest, relation row, 파생 index 데이터, vector/graph
  projection, task 상태, task event만 저장합니다. canonical 원본 데이터는 저장하지
  않습니다.

## 책임 경계

- **FoldMind 앱 서버:** 원본 문서, 원본 폴더, 원본 태그, 권한, 사용자,
  비즈니스 규칙을 소유합니다.
- **AI-Core:** freshness guard용 source manifest, 파생 index 데이터,
  vector/graph projection, 검색 결과, 생성 결과, workflow 상태, 제안된
  host action을 소유합니다.

AI-Core는 앱 서버를 직접 호출하지 않습니다. 폴더 생성, 문서 이동처럼 원본 데이터를
바꾸는 작업은 AI-Core가 직접 실행하지 않고 `HostAction`으로 반환합니다. 앱 서버가
그 action을 승인, 실행, 거절, 수정하고 실행 결과를 AI-Core에 다시 보냅니다.

## 주요 기능

**문서 인덱싱**

앱 서버가 `SourceDocument` snapshot을 보냅니다. AI-Core는 본문을 검색하기 쉬운
문서 조각(`DocumentChunk`)으로 나눕니다. AI-Core는 현재 digest 상태를
`DocumentIndexRecord`로 저장하고, LLM은 summary, concept, entity, issue,
commitment, claim 근거를 담은 `DocumentSignal`을 생성합니다.

인덱싱 요청은 PostgreSQL transaction 안에서 다음 상태를 원자적으로 저장합니다.

- source manifest
- 선택적 folder relation snapshot
- index record
- signal
- outbox event

Folder relation snapshot은 문서 `source_version`과 같은 `source_version`을 가져야
합니다.
빈 snapshot은 최신 empty membership으로 저장합니다.
snapshot을 생략하면 기존 membership을 바꾸지 않습니다.

Outbox event는 database-generated sequence, idempotency key, generated
`partition_key`를 사용합니다.
Delete event idempotency key에는 현재 `source_version`을 포함합니다.
그래야 재인덱싱 후 다시 삭제되는 이벤트가 중복으로 삼켜지지 않습니다.

Debezium Kafka consumer는 outbox event를 읽어 비동기로 embedding과 projection을
수행합니다.

- Qdrant에는 chunk, signal, folder, 문서 단위 vector를 저장합니다.
- Graph DB에는 `Document`-`Folder`, `Document`-`DocumentSignal`,
  `Folder`-`FolderSignal`, `FolderSignal`-`Document`, 폴더 계층 관계를 저장합니다.
- Neo4j projection 상태는 PostgreSQL ledger로 중복 저장하지 않습니다.
  복구는 outbox replay와 Kafka dead-letter 처리로 수행합니다.
- Chunk 본문은 Qdrant에 저장하고 graph DB에는 chunk node를 만들지 않습니다.

**폴더 인덱싱**

앱 서버가 `SourceFolder` snapshot을 보냅니다. AI-Core는 폴더 metadata와 그 폴더에
대한 가벼운 index 상태를 저장합니다. Projection worker가 outbox event를 소비해 name,
path, description을 Qdrant folder collection에 embedding하고, graph DB에는 `Folder`
node와 폴더 계층 관계를 저장합니다.

폴더 인덱싱은 `folder_sources`와 `folder_index_records`만 저장하고 별도 폴더 설명
테이블을 만들지 않습니다. 폴더 표시명, path, description, hierarchy는 다시 만들 수
있는 검색용 파생 인덱스이며, 원본 표시 정보와 권한의 기준은 앱 서버입니다.

**문서 검색**

문서 검색은 workflow step이 사용하는 application service입니다.

1. Qdrant는 질문과 의미가 비슷한 문서 조각과 문서를 vector similarity로 찾습니다.
2. PostgreSQL keyword search가 lexical chunk match를 더합니다.
3. Graph DB는 같은 폴더와 추출된 signal로 연결된 문서를 찾습니다.
4. AI-Core는 dense, keyword, document-level, graph signal을 병합해 chunk 순위를 만듭니다.

**질문 답변**

질문 답변은 workflow task로 실행합니다. Workflow가 관련 문서를 검색하고 검색 context를
LLM 입력으로 포맷한 뒤, 생성된 답변과 citation을 task result에 담아 반환합니다.

**추천**

폴더 추천은 workflow recommendation step으로 실행합니다.
AI-Core는 후보 `folder_id`, score, reason을 반환합니다.
원본 데이터 변경 적용은 앱 서버가 담당합니다.

**워크플로우**

`/tasks`는 자연어 요청을 받습니다.

AI-Core는 요청을 다음 실행 단계로 나눕니다.

- 검색
- 추천
- 요약
- 답변
- 초안 작성
- 아이디어 생성
- host action 계획

AI 단계는 AI-Core가 직접 실행합니다.
원본 데이터를 바꾸는 단계는 `HostAction`으로 반환하고 앱 서버의 실행 결과를 기다립니다.

## 앱 서버의 대표 호출 흐름

### 1. 문서 인덱싱

1. 앱 서버가 `POST /indexing/documents`에 제목, 본문, aggregate `source_version`,
   metadata, 선택적 `folder_relation_snapshot.folder_ids`를 보냅니다.
2. AI-Core가 tenant, 원본 식별자, 버전, 검색 가능한 본문을 검증합니다.
3. AI-Core가 본문을 `DocumentChunk` 목록으로 나눕니다.
4. LLM이 summary, concept, entity, issue, commitment, claim signal을 생성합니다.
5. PostgreSQL에 source manifest, 전달된 relation row, index record, signal,
   transactional outbox event를 저장합니다.
6. Projection worker가 embedding을 만들고 Qdrant와 graph DB record를 projection합니다.
7. 앱 서버는 생성된 chunk 개수를 받습니다.
8. 원본 문서 소유권은 앱 서버에 남습니다.

### 2. Workflow task로 질문 답변

1. 앱 서버가 `POST /tasks`에 자연어 질문, tenant, 선택적 context를 보냅니다.
2. AI-Core가 Qdrant 문서 vector와 graph DB 관계로 관련 문서 ID를 찾습니다.
3. AI-Core가 관련 문서 안에서 chunk를 검색합니다.
4. 관련 문서 ID가 없으면 요청된 검색 범위 안에서 바로 chunk를 찾습니다.
5. Context generation agent가 검색 context를 근거로 답변을 작성합니다.
6. 앱 서버는 답변 text와 citation이 담긴 task snapshot을 받습니다.

### 3. 워크플로우 task 실행

1. 앱 서버가 `POST /tasks`에 tenant와 자연어 요청을 보냅니다.
2. AI-Core가 task ID와 첫 task input ID를 생성합니다.
3. 앱 서버는 `POST /tasks/{task_id}/inputs`로 같은 task에 input을 추가할 수 있습니다.
4. Planning agent가 active 요청을 실행 가능한 workflow step으로 바꿉니다.
5. AI-Core가 검색, 추천, 요약, 답변, 초안 작성, 아이디어 생성 step을 실행합니다.
6. 원본 데이터를 바꾸는 step은 `HostAction`으로 task snapshot에 담습니다.
7. 앱 서버가 action을 승인, 실행, 거절, 수정, skip, retry 중 하나로 처리합니다.
8. 앱 서버가 `POST /tasks/actions/result`로 처리 결과를 AI-Core에 보냅니다.
9. AI-Core가 저장된 checkpoint에서 workflow를 이어 실행하고 최신 snapshot을 반환합니다.

## REST API

모든 REST DTO는 알 수 없는 field를 거부합니다.

- 입력 검증 오류는 `422`로 반환됩니다.
- task나 recommendation target을 찾지 못한 경우 해당 route는 `404`를 반환합니다.

### System

- `GET /health`
  process가 살아 있는지 확인합니다.
  정상 응답: `{"status": "ok"}`.

### Indexing

- `POST /indexing/documents`
  Request: `IndexDocumentRequest`.
  Response: `IndexDocumentResponse`.
  문서 snapshot을 인덱싱하고 생성된 chunk 개수를 반환합니다.
- `DELETE /indexing/documents/{document_id}`
  Response: `204 No Content`.
  source manifest를 삭제 표시하고 문서 파생 상태를 제거합니다.
- `POST /indexing/folders`
  Request: `IndexFolderRequest`.
  Response: `IndexFolderResponse`.
  폴더 snapshot을 인덱싱하고 검색용 folder 모델을 반환합니다.
- `DELETE /indexing/folders/{folder_id}`
  Response: `204 No Content`.
  folder source/index 상태를 삭제 표시하고 폴더 파생 상태를 제거합니다.

### Retrieval And Recommendations

문서, signal, folder retrieval은 workflow step이 사용하는 application service입니다.
현재 API에서는 독립 HTTP route로 노출하지 않습니다.

### Workflow Tasks

- `POST /tasks`
  Request: `CreateTaskRequest`.
  Response: `TaskSnapshotResponse`.
  자연어 input으로 task를 시작합니다.
- `POST /tasks/{task_id}/inputs`
  Request: `AppendTaskInputRequest`.
  Response: `TaskSnapshotResponse`.
  기존 task에 input을 추가하고 다시 계획합니다.
- `GET /tasks/{task_id}`
  Response: `TaskSnapshotResponse`.
  앱 서버가 볼 수 있는 최신 task snapshot을 조회합니다.
- `DELETE /tasks/inputs/{task_input_id}`
  Response: `TaskSnapshotResponse`.
  input entry를 removed로 표시하고 active input으로 다시 계획합니다.
- `POST /tasks/actions/result`
  Request: `RecordHostActionResultRequest`.
  Response: `RecordHostActionResultResponse`.
  host action 처리 결과를 받아 중단된 workflow를 재개합니다.

## 검색 동작

문서 검색은 `DocumentSearchService`와 그 아래 retrieval service들이 함께 실행합니다.

1. 질문 text를 embedding으로 변환합니다.
2. Qdrant `documents` collection에서 질문과 가까운 문서 ID를 찾습니다.
3. Graph DB에서 폴더와 추출된 signal로 연결된 관련 문서 ID를 찾습니다.
4. 2번과 3번에서 문서 ID가 나오면 그 문서들 안에서 chunk vector 검색을 실행합니다.
5. 문서 ID가 나오지 않으면 요청의 `SearchScope`만 적용해 chunk vector 검색을 실행합니다.
6. hybrid retrieval이 dense/keyword 결과를 병합합니다.
7. document-level boost를 적용해 가장 높은 순위의 chunk를 반환합니다.

현재 Qdrant adapter는 dense chunk vector, document-level vector, signal vector,
folder vector를 구현합니다.

## 워크플로우 생명주기

워크플로우 API는 AI-Core가 추론과 제안을 맡고, 앱 서버가 원본 데이터 변경을 통제하는
구조입니다.

**시작과 재계획**

1. 앱 서버가 `POST /tasks`에 tenant와 자연어 input을 보냅니다.
2. AI-Core가 `task_id`와 `task_input_id`를 생성합니다.
3. 이후 `POST /tasks/{task_id}/inputs`를 호출하면 기존 task에 input을 추가합니다.

**계획과 실행**

1. `TaskWorkflowService`가 현재 `TaskSnapshot`을 저장합니다.
2. service가 workflow runtime을 호출합니다.
3. `PlanningAgent`가 active 요청들을 `WorkflowPlan`으로 바꿉니다.
4. `WorkflowPlanCompiler`가 plan을 실행 가능한 step 목록으로 바꿉니다.
5. `WorkflowStepExecutor`가 각 step을 검색, 추천, 생성, host-action planning으로
   보냅니다.
6. `WorkflowArtifactRegistry`가 step 결과를 기록합니다.
7. 기록된 결과는 앱 서버가 볼 수 있는 `TaskFinalResult`로 노출됩니다.

**중단, 재개, 완료**

1. host action이 만들어지면 workflow는 checkpoint를 저장하고 중단됩니다.
2. 앱 서버는 `DELETE /tasks/inputs/{task_input_id}`로 input entry를 removed 처리할 수
   있습니다.
3. 앱 서버가 `POST /tasks/actions/result`로 action 처리 결과를 보냅니다.
4. workflow가 checkpoint에서 재개됩니다.
5. 남은 step과 pending action이 없으면 최종 `TaskSnapshot`이 저장됩니다.

## Agents

Agent는 하나의 prompt-backed LLM 작업을 담당하는 application-layer component입니다.
agent는 OpenAI SDK에 직접 의존하지 않고 `LLMProvider`와 `PromptStore`에
의존합니다.

- `PlanningAgent`
  `WorkflowEngine.prepare()`에서 `workflow_planning` prompt를 사용합니다.
  자연어 task를 검증된 `WorkflowPlan`으로 바꿉니다.
- `DocumentSignalExtractorAgent`
  `DocumentIndexingService`에서 `document_signal_extraction` prompt를 사용합니다.
  문서와 chunk를 분석해 `DocumentIndexRecord`와 `DocumentSignal` 집합을 생성합니다.
- `ContextGenerationAgent`
  retrieval과 workflow generation step에서 `answer_generation`, `summarization`,
  `draft_generation`, `ideas_exploration` prompt를 사용합니다.
  검색된 chunk를 근거로 cited text를 생성합니다.

Context generation agent는 검색된 chunk를 LLM에 전달하기 전에
`UNTRUSTED_CONTEXT_INSTRUCTION`을 prompt에 넣습니다. planner는
`ALLOWED_WORKFLOW_ACTION_TYPES`를 prompt에 넣어 runtime이 지원하는 action만 선택하게
합니다.

## 도메인 모델

- **Source snapshot:** `SourceDocument`, `SourceFolder`.
  앱 서버가 보낸 원본 데이터의 현재 상태 복사본입니다.
- **Retrieval/index model:** `DocumentChunk`, vector projection model,
  `RetrievedDocument`, `RetrievedFolder`.
  AI-Core가 만든 저장소별 projection과 retrieval-facing reference입니다.
- **Signal:** `DocumentSignal`, `FolderSignal`.
  Summary, concept, entity, issue, commitment, claim 결과입니다.
- **Retrieval:** `RetrievalQuery`, `RequestContext`, `SearchScope`, `QueryAnchor`.
  질문 text, tenant 정보, 검색 범위, anchor입니다.
- **Generation:** `GeneratedTextResult`, `DraftResult`, recommendation result,
  clarification result.
- **Workflow:** `TaskInputEntry`, `TaskSnapshot`, `TaskAnalysis`,
  `TaskFinalResult`, `TaskEvent`.
- **Host action:** `HostAction`, `HostActionResult`, typed action payload.
- **Graph projection:** `ProjectDocumentCommand`,
  `ProjectDocumentFolderRelationsCommand`, `ProjectFolderCommand`,
  `ProjectFolderSignalsCommand`.
- **Outbox event:** `OutboxEvent`.
  PostgreSQL source, relation, index, signal 변경과 같은 transaction에서 발행되는
  projection 입력 event입니다.

중요한 규칙:

- source model은 snapshot입니다.
- 원본 데이터의 기준은 앱 서버입니다.
- indexed model, index record, signal은 다시 만들 수 있는 파생 상태입니다.
- `TaskFinalResult`는 type이 정해져 있습니다.
- 예를 들어 `summary` result는 generated text를 담아야 합니다.
- host action payload는 `HostActionType`과 맞아야 합니다.
- DTO가 API 입력을 검증한 뒤 mapper가 application command/query를 만듭니다.

## 데이터 저장

AI-Core는 AI 파생 상태만 저장합니다. 원본 문서, 원본 폴더, 원본 태그, 권한은 저장하지
않습니다. 원본 태그가 필요하면 source metadata의 opaque 값으로만 전달하며, AI-Core는
이를 graph 관계나 검색 scope로 승격하지 않습니다.

### PostgreSQL

- **`tenant_storage_scopes`** (`tenant_id`):
  tenant 단위 AI-Core 저장 범위와 retention 상태입니다.
- **`document_sources`, `folder_sources`** (source IDs):
  현재 source manifest입니다.
  source identity, aggregate source version,
  digest/size 또는 folder metadata, timestamp, 삭제 상태, opaque source
  metadata를 저장합니다.
  원문 body는 저장하지 않습니다.
- **`source_document_folder_relations`**
  (`tenant_id`, `document_id`, `folder_id`):
  document relation snapshot에서 온 현재 folder membership row입니다. row가
  없으면 현재 empty membership입니다.
- **`document_index_records`, `document_chunks`, `folder_index_records`**
  (source IDs / chunk UUIDs):
  현재 파생 index manifest와 document chunk record입니다.
- **`document_signals`, `folder_signals`** (`signal_id`):
  추출된 signal text, payload, evidence, confidence, extractor metadata,
  document/folder signal input digest, generation version, 선택적 generation
  model을 저장합니다.
- **`vector_projection_records`** (`collection_name`, `point_id`):
  Qdrant write ledger입니다. source row FK 없이 collection, point ID, source
  identity, vector item identity, source input digest, vector input digest를
  기록합니다.
- **`outbox_events`** (`event_id` UUID):
  Kafka/Debezium transactional outbox event입니다. `tenant_id`,
  `idempotency_key`, `event_sequence`, `partition_key`, `event_type`으로 stream
  ordering, idempotency, dead-letter context를 제공합니다.
- **`tasks`** (`task_id` UUID):
  현재 task aggregate status, active input text, analysis message, current
  action, error, metadata를 저장합니다.
- **`task_inputs`** (`task_input_id` UUID):
  task 안에 쌓인 사용자 요청 entry와 active/removed 상태입니다.
- **`task_jobs`, `task_job_results`** (UUID job/result IDs):
  계획된 workflow job, 실행 상태, typed result payload, task-local
  ordering입니다.
- **`host_actions`** (`action_id` UUID):
  제안된 host action, typed input payload, result payload, policy JSON,
  task-local 순차 ordering을 저장합니다.
- **`task_events`** (`event_id` UUID):
  task event log입니다.

PostgreSQL schema는 Alembic으로 관리합니다.
API를 시작하기 전에 migration을 실행합니다.

```bash
FOLDMIND_POSTGRES_DSN=postgresql://user:password@host:5432/foldmind_ai_core alembic upgrade head
```

초기 migration chain은 최적화된 최초 버전의 파생 상태 schema, Kafka outbox,
Qdrant vector ledger, workflow task table을 생성합니다.

### Qdrant

- **`FOLDMIND_QDRANT_DOCUMENT_CHUNK_COLLECTION`**
  - 기본 collection: `document_chunks`
  - Payload kind: `document_chunk`
  - 목적: chunk 본문 vector search
- **`FOLDMIND_QDRANT_DOCUMENT_COLLECTION`**
  - 기본 collection: `documents`
  - Payload kind: `document`
  - 목적: 문서 제목과 추출된 signal text 기반 문서 단위 vector search
- **`FOLDMIND_QDRANT_SIGNAL_COLLECTION`**
  - 기본 collection: `signals`
  - Payload kind: `signal`
  - 목적: 추출된 document/folder signal 단위 vector search
- **`FOLDMIND_QDRANT_FOLDER_COLLECTION`**
  - 기본 collection: `folders`
  - Payload kind: `folder`
  - 목적: 폴더 discovery와 추천을 위한 folder metadata vector search

### Graph DB

Graph DB는 표준 AI-Core API의 필수 저장소입니다. 인덱싱 요청 경로가 graph DB에
동기적으로 기록하지는 않습니다. Projection worker가 outbox event를 소비해 graph
관계를 멱등하게 갱신합니다.

- **`Document`-`Folder` (`IN_FOLDER`):** 문서가 어떤 폴더에 속하는지 나타냅니다.
- **`Document`-`DocumentSignal` (`HAS_SIGNAL`):** 문서 버전에 추출된 document
  signal을 연결합니다.
- **`Folder`-`Folder` (`CHILD_OF`):** 폴더 계층 관계입니다.
- **`Folder`-`FolderSignal` (`HAS_SIGNAL`):** 폴더에서 파생된 signal을 폴더에
  연결합니다.
- **`FolderSignal`-`Document` (`ABOUT_DOCUMENT`):** 특정 문서를 지목하는
  folder-derived signal의 선택적 관련 문서 관계입니다.

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
Inbound application ports
  HTTP와 messaging entrypoint가 호출하는 typed protocol
        |
        v
Application services
  indexing / projection / workflow entrypoint
  retrieval과 recommendation 정책은 service와 workflow step에 둡니다
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

- **`core/domain/models/`:** business model입니다. 외부 framework에 의존하지
  않습니다.
- **`core/domain/services/`:** concept normalization, confidence validation,
  outbox invariant 같은 순수 domain rule입니다.
- **`core/application/ports/inbound/`:** inbound adapter가 호출하는
  protocol입니다.
  Concrete application service가 구조적으로 구현합니다.
- **`core/application/ports/outbound/`:** LLM provider, embedding provider,
  repository, vector store, graph store, prompt store, workflow runtime
  interface입니다.
- **`core/application/models/`:** application service command, query, result,
  retrieval model, projection model, workflow flow-state model입니다.
- **`core/application/mappers/`:** boundary mapping과 domain-to-application
  mapping 함수입니다.
- **`core/application/services/`:** indexing, retrieval, recommendation,
  projection, workflow 책임별 inbound application API와 application
  policy입니다.
- **`core/application/formatters/`, `execution/`, `prompts.py`:** service가
  아닌 application support code입니다.
- **`core/application/agents/`:** prompt-backed AI 작업입니다.
- **`core/application/workflows/`:** workflow step 실행, artifact 저장,
  host action 처리 정책입니다.
- **`adapters/inbound/http/`:** FastAPI router, REST DTO, HTTP error
  mapping입니다.
- **`adapters/outbound/`:** PostgreSQL, Qdrant, graph DB, OpenAI, LangGraph,
  file prompt store 구현입니다.
- **`bootstrap/`:** 설정을 읽고 concrete adapter와 application service를 port
  뒤에 연결합니다.

## 배포와 설정

이 repository는 endpoint 기반 설정을 사용합니다.

- 전역 `DB_MODE=local/cloud` 값은 없습니다.
- PostgreSQL, Qdrant, graph DB endpoint를 각각 설정합니다.
- Dockerfile과 Compose manifest는 아직 없습니다.

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
`FOLDMIND_NEO4J_USER`, `FOLDMIND_NEO4J_PASSWORD`, `FOLDMIND_AI_PROVIDER=openai`일 때의
`FOLDMIND_OPENAI_API_KEY`, `FOLDMIND_EMBEDDING_MODEL`, `FOLDMIND_EMBEDDING_VERSION`,
`FOLDMIND_CHUNKING_VERSION`, `FOLDMIND_INDEX_SCHEMA_VERSION`,
`FOLDMIND_DOCUMENT_SIGNAL_EXTRACTION_PROMPT_VERSION`은 표준 configured API에서
필수입니다.

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
      application/   service, port, agent, workflow policy
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
PYTHONPATH=src python -m compileall -q src tests migrations scripts
PYTHONPATH=src python -m unittest discover -s tests
python -m pip install -e ".[dev]"
ruff check src tests
mypy src
```

- `scripts/run_api.sh`는 configured ASGI app을 실행합니다.
- `scripts/run_worker.sh`는 Kafka outbox projection worker를 실행합니다.

outbox worker는 `FOLDMIND_OUTBOX_PROJECTION_TARGET`별로 하나씩 실행합니다.

지원 target:

- `qdrant-document-chunks`
- `qdrant-documents`
- `qdrant-signals`
- `qdrant-folders`
- `neo4j-graph`

worker는 target별 consumer group 이름을 자동으로 만듭니다. 그래서 각 projection
target이 같은 outbox stream을 독립적으로 consume합니다.

기본 outbox topic은 `indexing-events`입니다. Debezium Kafka message key는 generated
`partition_key` column으로 설정합니다.

실패 메시지는 `indexing-events.dlq`로 보냅니다. 원인을 수정한 뒤
`scripts/replay_dead_letter_events.py`로 재생합니다.

별도 checkpoint DSN 없이 local workflow bootstrap을 하려면
`FOLDMIND_ALLOW_IN_MEMORY_WORKFLOW_CHECKPOINT=true`를 설정합니다. 표준 configured API는
그래도 `FOLDMIND_POSTGRES_DSN`, `FOLDMIND_QDRANT_URL`, graph DB 설정을 요구합니다.

## 현재 한계

- Dockerfile과 Compose manifest가 아직 없습니다.
