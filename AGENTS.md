# AGENTS.md

이 문서는 AI 코딩 에이전트가 `foldmind-ai-core` 저장소에서 작업할 때 따라야 할 기준이다.

적용 대상은 코드 수정, 리팩토링, 기능 추가, 테스트 작성, 문서화다.

현재 코드베이스에는 정리되지 않은 패턴이나 리팩토링 잔재가 남아 있을 수 있다.
기존 코드를 무조건 모방하지 말고, 이 문서의 방향을 앞으로의 기준으로 삼는다.

## 1. 프로젝트 목표

이 프로젝트는 FoldMind 개인 지식 관리 제품을 위한 AI-Core 시스템이다.

AI-Core는 다음을 담당한다.

- 문서 검색
- 폴더 추천
- 관련 문서 추천
- Q&A
- 요약
- 초안 생성
- 아이디어 탐색
- 액션 플랜 생성
- 인덱싱
- 임베딩 생성
- retrieval
- 그래프 기반 관계 분석
- AI workflow 실행
- 검색/RAG/workflow용 파생 projection 저장

이 프로젝트는 다음을 우선한다.

- 단순하고 읽기 쉬운 코드
- 명확한 책임 분리
- 유지보수하기 쉬운 구조
- 명시적인 네이밍
- 과도하지 않은 추상화
- 레거시가 남지 않는 리팩토링
- 명시적으로 요청되지 않은 기존 동작 변경 금지
- 테스트 가능한 코드
- 애플리케이션 로직, 도메인 로직, 인프라 로직의 명확한 경계

## 2. 데이터 소유권

App Server는 원본 사용자 데이터의 source of truth다.

App Server가 소유한다.

- 원본 문서
- 원본 폴더
- 원본 폴더-문서 관계
- 원본 태그
- 사용자 권한
- 사용자/조직/tenant 정책
- 비즈니스 규칙
- 사용자가 최종 승인한 변경 결과

폴더-문서 관계는 문서별 `folder_relation_snapshot`으로 전달된다.

AI-Core는 관계 cardinality 정책을 소유하지 않는다.

- App Server가 문서별로 여러 `folder_id`를 보내면 n:n처럼 동작한다.
- App Server가 항상 하나 이하의 `folder_id`만 보내면 1:n처럼 동작한다.

문서의 `source_version`은 문서 본문만의 버전이 아니라 문서 aggregate version이다.

App Server는 다음 변경이 있을 때 해당 문서의 `source_version`을 반드시 증가시켜야 한다.

- title/content/metadata 변경
- 폴더 추가
- 폴더 제거
- 폴더 이동
- 폴더 membership 전체 비움

`folder_relation_snapshot.source_version`은 별도 relation version이 아니다.
문서 aggregate와 같은 `source_version`이어야 한다.

AI-Core에서 `source_version`은 stale 요청을 막는 aggregate freshness guard다.
Chunk, signal, vector point 같은 파생물의 identity는 파생물별 입력 digest를 기준으로 만든다.
`source_version` 자체를 파생물 identity로 쓰지 않는다.

따라서 폴더 membership만 바뀌어 `source_version`이 증가해도 파생물 identity는 유지될 수 있다.
본문 입력과 indexing 정책이 같으면 content chunk/vector/signal identity는 바뀌지 않아야 한다.

Digest 이름은 파생물 책임을 드러내야 한다.

| 대상 | Digest |
| --- | --- |
| 문서 chunk/search 입력 | `document_index_input_digest` |
| 문서 signal 입력 | `document_signal_input_digest` |
| 폴더 source projection 입력 | `folder_index_input_digest` |
| folder-derived signal 입력 | `folder_signal_input_digest` |
| Qdrant/ledger upstream digest | `source_input_digest` |
| 실제 float vector 생성 입력 | `vector_input_digest` |

Folder-derived signal도 숫자 revision이 아니라 `folder_signal_input_digest`로 freshness를 판단한다.

이 digest는 다음 값을 해시한 folder signal 입력 identity다.

- `folder_index_input_digest`
- 현재 folder subtree member document들의 `document_id`
- member document들의 `content_digest`
- member document들의 `document_index_input_digest`
- member document들의 `document_signal_input_digest`
- `signal_generation_version`

늦게 도착한 folder signal invalidation event는 조건부로만 처리한다.
event의 digest가 현재 folder index record와 일치할 때만 stale signal projection을 삭제해야 한다.

`signal_generation_version`은 독립 컬럼이다.
현재 저장된 signal set이 어떤 signal 생성 정책 버전으로 만들어졌는지 나타낸다.

다음처럼 signal set 자체가 달라지는 변경은 이 버전으로 드러나야 한다.

- Signal type 추가/제거
- prompt 정책 변경
- extractor schema 변경

문서별 folder relation은 별도 state table을 두지 않는다.
`source_document_folder_relations` membership row로만 저장한다.

- `folder_relation_snapshot`이 생략되면 기존 membership을 변경하지 않는다.
- snapshot이 제공됐고 relation row가 0개이면 최신 empty membership으로 해석한다.
- relation update의 `source_version`이 현재 `document_sources.source_version`과
  정확히 같을 때만 membership row를 교체한다.

LLM 모델명은 index record의 freshness key가 아니다.
실제 생성물 provenance가 필요한 경우 signal row에 둔다.
예를 들면 `document_signals.generation_model` 또는 `folder_signals.generation_model`이다.
Deterministic extractor 결과는 `generation_model`이 없을 수 있다.

AI-Core는 canonical user data를 소유하지 않는다.

AI-Core가 소유할 수 있는 것은 freshness guard로 쓰는 source manifest와 AI/index 파생 데이터다.

- document/folder source manifest
- source document folder relation membership row
- 문서 chunk
- embedding
- vector index
- graph projection
- 문서 index record
- 문서/folder signal
- 검색 결과
- 생성된 중간 artifact
- workflow task/action/output/event 상태

AI-Core는 canonical user data를 직접 변경하지 않는다.
원본 데이터 변경이 필요하면 action plan 또는 host action을 반환한다.
최종 실행은 App Server가 담당한다.

## 3. 아키텍처 방향

이 프로젝트는 Hexagonal Architecture를 주요 아키텍처 방향으로 사용한다.

계층의 의미는 다음과 같다.

- `core/domain/models`: 핵심 비즈니스 개념
- `core/domain/services`: 순수 도메인 규칙
- `core/application`: application service와 애플리케이션 흐름
- `core/application/ports`: application 계층이 필요로 하는 인터페이스
- `adapters`: DB, 외부 API, LLM, Vector DB, Graph DB, framework 구현체
- `adapters/inbound/http`: HTTP 외부 진입점
- `adapters/inbound/messaging`: outbox worker와 메시징 consumer 진입점

의존성 방향은 반드시 지킨다.

- Application은 외부 기술을 모른다.
- Application은 Port Interface에만 의존한다.
- Adapter는 Application의 Port를 구현하거나 Inbound Port를 호출한다.
- 외부 프레임워크, DB, SDK는 Adapter 내부에 격리한다.
- HTTP router, messaging consumer, worker entrypoint는 Inbound Adapter다.
- PostgreSQL, Qdrant, Neo4j, OpenAI, Kafka producer는 Outbound Adapter다.

## 4. 저장소 책임

저장소 간 책임을 섞지 않는다.

PostgreSQL은 다음을 담당한다.

- document/folder source manifest
- source document folder relation membership row
- document/folder index record 최신 상태
- document/folder signal 최신 상태
- vector projection ledger 최신 상태
- workflow task/action/output/event 상태
- transactional outbox event

Qdrant는 다음을 담당한다.

- chunk text 기반 vector 검색
- document-level vector 검색
- document/folder signal vector 검색
- folder metadata vector 검색

Neo4j는 다음을 담당한다.

- `Document`, `Folder`, `DocumentSignal`, `FolderSignal` node projection
- `Document`-`Folder`의 `IN_FOLDER` 관계
- `Document`-`DocumentSignal`과 `Folder`-`FolderSignal`의 `HAS_SIGNAL` 관계
- `FolderSignal`-`Document`의 선택적 `ABOUT_DOCUMENT` 관계
- `Folder`-`Folder`의 `CHILD_OF` folder hierarchy
- graph 기반 탐색과 추천 보강

각 저장소는 자기 책임 외의 데이터를 소유하지 않는다.

- folder 관계의 단일 projection은 Neo4j다.
- Qdrant payload에 folder 관계를 중복 저장하지 않는다.
- 태그는 App Server의 원본 metadata로만 취급한다.
- 태그를 AI-Core의 graph/search 개념으로 승격하지 않는다.

## 5. Outbox와 정합성

PostgreSQL, Qdrant, Neo4j의 정합성은 Transactional Outbox와 비동기 projection worker로 맞춘다.

인덱싱 요청 경로는 PostgreSQL transaction 안에서 다음까지만 책임진다.

- source manifest 저장 또는 삭제
- 선택적으로 `source_document_folder_relations` membership row 교체
- index record와 signal 저장 또는 삭제
- outbox event 저장

Qdrant/Neo4j projection은 outbox event를 소비하는 worker가 수행한다.

Worker는 at-least-once delivery를 전제로 멱등하게 작성한다.

- 같은 이벤트가 여러 번 처리되어도 최종 상태는 한 번 처리한 것과 같아야 한다.
- Qdrant point id는 고정 ID를 사용한다.
- Neo4j는 `MERGE`와 관계 replace를 사용한다.
- delete event는 여러 번 처리되어도 성공으로 취급한다.

## 6. 네이밍 규칙

이름은 역할을 설명해야 한다.

- `Repository`: 저장소에 대한 읽기/쓰기 port 또는 구현체
- `Adapter`: 외부 기술 또는 framework와 application을 연결하는 구현체
- `Client`: 외부 SDK, DB connection, HTTP client 같은 low-level 접근 객체
- `Application Service`: 외부 inbound adapter가 호출하는 application-level 흐름
- `Domain Service`: framework나 port 없이 domain model만 다루는 순수 규칙
- `Provider`: LLM, embedding model, 설정값처럼 외부 capability를 제공하는 객체
- `DTO`: 외부 API, 메시지, framework boundary에서 사용하는 입출력 모델
- `Domain`: 비즈니스 개념과 규칙을 표현하는 모델
- `Request / Response Model`: API 또는 messaging boundary의 명시적 입출력 모델

`Manager`, `Helper`, `Util`, `Processor`처럼 의미가 흐린 이름은 강한 이유가 없다면 피한다.
필요하면 더 구체적인 이름을 사용한다.

## 7. Application Service 규칙

Application Service는 inbound port를 구현하는 application API다.

HTTP router, messaging consumer, worker entrypoint는 inbound port protocol에만 의존한다.
Concrete application service는 bootstrap composition root에서만 조립한다.

Application Service의 기본 역할은 다음으로 제한한다.

- command/query를 application 흐름에 맞게 처리
- 여러 repository와 outbound port 조합
- transaction boundary 조율
- workflow 실행과 저장 흐름 조율
- application-level 예외를 명확히 변환
- 결과 반환 형태 조립
- 필요한 순수 도메인 규칙을 `core/domain/services`에서 호출

Application Service는 다음을 하면 안 된다.

- PostgreSQL, Qdrant, Neo4j, OpenAI SDK를 직접 import
- FastAPI, Kafka, HTTP framework에 직접 의존
- adapter 구현체를 직접 생성
- 저장소별 세부 query나 SDK payload를 직접 구성
- DTO/API boundary 입력 검증을 반복

Application Service는 다음 정책을 파일 내부에 흩뜨리지 않는다.

- ranking, scoring, dedupe, boost, merge 정책
- retrieval mode 분기 정책
- graph/vector scope 변환 정책
- workflow request queue 상태 조작 정책
- projection metadata spec 조립
- 반복되는 상태 초기화 또는 상태 전이 규칙
- 저장소 구현명이 드러나는 변수명 또는 메서드명

이런 로직은 같은 service 패키지의 명확한 정책 객체나 private helper로 분리한다.

예시:

- `DocumentRetrievalService`: dense/keyword/hybrid/comprehensive retrieval 흐름
- `FolderRetrievalService`: folder retrieval fan-out, signal 수집, ranking 호출
- `FolderRetrievalRanker`: folder score 집계, reason 병합, ranking
- `RelationshipScopeResolver`: folder scope를 document search scope로 변환
- `VectorProjectionSpec`: vector projection에 필요한 embedding/index metadata 묶음

순수 도메인 규칙은 `core/domain/services`로 분리한다.

예시:

- `DocumentChunker`: source document를 document chunk로 나누는 정책과 chunk metadata 부여
- `WorkflowInputService`: task request append/remove, active request text 재계산, replanning 상태 초기화
- signal concept, confidence, outbox invariant 검증처럼 framework나 port 없이 domain model만 다루는 규칙

## 8. Agent 및 Orchestrator 규칙

AI Agent와 Orchestrator는 통제 가능하고 명시적으로 설계한다.

Agent는 하나의 prompt-backed LLM 작업을 담당한다.

- Agent는 OpenAI SDK에 직접 의존하지 않는다.
- Agent는 LLM port와 prompt store port에 의존한다.
- Agent 입력/출력은 명시적인 domain/application 모델로 정의한다.
- prompt key, 모델 입력, 출력 parsing 책임을 숨기지 않는다.

Orchestrator는 여러 step의 실행 흐름을 조율한다.

- 원본 데이터 변경은 직접 실행하지 않는다.
- App Server가 실행할 host action을 명시적으로 반환한다.
- retry, skip, approval, failure 흐름은 task 상태로 드러나야 한다.

## 9. 리팩토링 규칙

리팩토링 시 반드시 지킨다.

- 명시적으로 요청되지 않은 동작 변경 금지
- 네이밍 개선 우선
- 중복 제거
- 큰 함수/클래스는 책임 기준으로 분리
- 불필요한 추상화 제거
- 명확한 가치 없이 복잡한 패턴 도입 금지
- 위험한 코드 변경 전 중요한 동작에 대한 테스트 추가
- 레거시 호환 레이어는 명시적으로 요구되지 않으면 남기지 않는다
- 죽은 코드, no-op 메서드, 의미 없는 wrapper는 제거한다

현재 구조가 이 문서와 충돌하면 기존 구조를 무조건 따르지 않는다.
이 문서의 방향에 맞춰 정리한다.

## 10. 테스트 규칙

테스트는 구현 세부사항보다 동작을 검증해야 한다.

우선순위는 다음과 같다.

- public API contract
- application service behavior
- repository persistence behavior
- outbox transaction behavior
- worker idempotency
- graph/vector projection 결과
- adapter boundary mapping

리팩토링의 목적이 기존 동작 보존이라면 테스트를 먼저 작성한다.
테스트는 변경 전후 결과가 같다는 점을 검증해야 한다.

테스트 실행 기준은 기본적으로 다음을 사용한다.

```bash
PYTHONPATH=src python -m compileall -q src tests migrations scripts
PYTHONPATH=src python -m unittest discover -s tests
```

Ruff와 mypy 설정은 `pyproject.toml`을 따른다.

## 11. 코드 작성 기준

코드는 단순해야 한다.

- 불필요한 중간 레이어를 만들지 않는다.
- 함수는 한 가지 책임을 갖게 한다.
- 조건문 중첩은 줄인다.
- 변수명은 축약하지 않는다.
- 데이터 변환 흐름은 명시적으로 보이게 한다.
- tuple/list/dict/json 변환은 boundary 근처에 둔다.
- domain 모델에 framework validation 책임을 넣지 않는다.
- DTO에서 외부 입력 검증을 담당한다.
- Application Service에서 DTO/API 입력 검증을 반복하지 않는다.
- Application Service 안에서 `require_non_blank`, `require_uuid` 같은 boundary
  validation을 반복하지 않는다.
- 단, 다음 application 상태는 Application Service에서 명시적으로 처리할 수 있다.
  - repository 조회 결과 없음
  - workflow task 없음
  - 후보 결과 없음

네이밍은 구현 기술이 아니라 application 의미를 드러내야 한다.

- `qdrant_scope` 같은 저장소 구현명 대신 `document_search_scope`처럼 application 의미를 사용한다.
- `validator`가 실제로 결과를 걸러내는 역할이면 `result_filter`처럼 동작을
  설명하는 이름을 사용한다.

특히 projection 흐름은 명확해야 한다.

- `SourceDocument`와 `DocumentChunk`에서 chunk vector projection을 만든다.
- `DocumentSourceState`, `DocumentIndexState`, `DocumentSignal`에서 document-level vector projection을 만든다.
- `DocumentSignal`에서 document signal vector/graph projection을 만든다.
- `SourceDocumentFolderRelationSnapshot`에서 document-folder graph relation projection을 만든다.
- `SourceFolder`에서 folder vector projection과 folder hierarchy graph projection을 만든다.
- `FolderSignal`에서 folder signal vector/graph projection을 만든다.

서로 다른 저장소에 같은 책임을 중복 저장하지 않는다.

## 12. 변경 전 확인 사항

코드를 수정하기 전에 다음을 확인한다.

- 이 변경이 domain, application, adapter 중 어디에 속하는가
- 외부 동작이 바뀌는가
- DTO/API shape가 바뀌는가
- 저장소 schema나 payload가 바뀌는가
- outbox event payload와 worker 처리가 함께 바뀌어야 하는가
- 테스트가 기존 동작을 충분히 보호하는가

불확실하면 먼저 코드 흐름을 조사하고, 결정이 필요한 지점만 사용자에게 묻는다.

## 13. Application Service 기준

Application service는 inbound adapter가 호출하는 application entrypoint다.
반복되거나 비대해지는 application 정책을 담는다.

Application service로 분리해야 하는 경우는 다음과 같다.

- 여러 inbound adapter나 workflow에서 같은 정책을 공유한다.
- public method가 위에서 아래로 읽히지 않는다.
- ranking, scoring, dedupe, merge, filtering 정책이 application 흐름을 가린다.
- workflow 상태 조작이 여러 entrypoint에 퍼진다.
- 설정값 여러 개가 생성자에 흩어져 다닌다.
- bootstrap에서 조립해야 할 application value object가 service 내부에 섞인다.

Application service로 분리하지 않아도 되는 경우는 다음과 같다.

- 단일 application flow의 transaction boundary를 명확히 보여주는 작은 private method
- side effect 순서를 명확히 분리하는 helper
- 인라인하면 public method가 더 무거워지는 application 흐름
