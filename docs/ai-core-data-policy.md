# AI-Core 데이터 정책

이 문서는 FoldMind AI-Core가 데이터를 어떤 책임과 경계 안에서 저장하고 갱신하는지 정의한다.
구현 세부 스키마보다 장기 운영 정책을 우선한다.

## 1. 데이터 소유권

- App Server가 원본 사용자 데이터의 source of truth다.
- 원본 문서, 폴더, 폴더-문서 관계, 원본 태그, 권한, tenant 정책은 App Server가 소유한다.
- 폴더-문서 관계는 문서별 folder relation snapshot으로 전달된다.
- AI-Core는 관계 cardinality 정책을 소유하지 않는다. App Server가 문서별로 여러 `folder_id`를 보내면 n:n처럼 동작하고, 항상 하나 이하의 `folder_id`만 보내면 1:n처럼 동작한다.
- AI-Core는 원본 데이터를 canonical 데이터로 소유하지 않는다.
- AI-Core는 검색, 추천, 요약, 그래프 탐색, RAG를 위한 파생 데이터만 소유한다.
- 태그 정보가 필요하면 App Server가 source metadata에 opaque 값으로 전달할 수 있지만, AI-Core는 이를 태그 관계나 태그 검색 scope로 해석하지 않는다.

## 2. 최신 상태 유지

- AI-Core는 문서와 폴더에 대해 최신 입력과 최신 분석 결과만 유지한다.
- 같은 문서나 폴더가 다시 인덱싱되면 이전 분석 결과는 새 결과로 교체한다.
- 과거 버전별 입력, 과거 분석 결과, 과거 vector, 과거 graph projection은 보존하지 않는다.
- 과거 이력이 필요하면 App Server 또는 별도 감사/이력 시스템에서 관리한다.

## 3. 식별자

- `tenant_id`는 tenant를 식별한다.
- `document_id`는 App Server가 발급한 전역 유일 문서 ID다.
- `folder_id`는 App Server가 발급한 전역 유일 폴더 ID다.
- AI-Core는 `document_id`, `folder_id`를 기준으로 최신 상태를 갱신한다.
- ID 형식 검증 책임은 App Server에 둔다.

## 4. Source Version

- `source_version`은 App Server가 제공하는 source 변경 버전이다.
- 문서나 폴더의 의미 있는 입력이 바뀌면 App Server는 반드시 `source_version`을 바꿔야 한다.
- `source_version`은 같은 문서나 폴더 안에서 문자열 사전식 정렬로 비교 가능해야 하며, 의미 있는 입력이 바뀔 때마다 단조 증가해야 한다.
- AI-Core와 App Server 사이의 계약은 문자열 사전식 정렬에서 더 큰 `source_version`이 더 최신 source임을 보장한다.
- AI-Core는 오래된 비동기 작업 결과가 최신 결과를 덮어쓰지 못하도록 `source_version`을 기준으로 최신성을 확인한다.
- 문서는 본문 변경 여부도 함께 확인해 stale result를 막는다.

## 5. 분석 결과

- 문서 분석 결과는 항상 특정 문서에 속한다.
- 폴더 분석 결과는 항상 특정 폴더에 속한다.
- 문서나 폴더가 다시 인덱싱되면 기존 분석 결과를 교체한다.
- 분석 결과를 여러 버전으로 나누어 보존하지 않는다.
- 문서 삭제 시 그 문서를 포함하던 폴더의 폴더 signal은 함께 무효화한다.
- AI-Core는 삭제된 문서를 근거로 만든 폴더 signal을 보존하지 않으며, 필요한 경우 App Server가 폴더 책임 평가를 다시 요청해 최신 signal을 만든다.

## 6. Signal

- Signal은 AI-Core가 문서나 폴더에서 추출한 의미 단위다.
- 문서 signal과 폴더 signal은 서로 다른 책임을 가지므로 분리한다.
- 문서 signal은 문서 요약, 개념, 엔티티, 이슈, 약속, 주장 등을 표현한다.
- 폴더 signal은 폴더 요약, 책임 적합도, 응집도, 이상 문서, 커버리지 공백, 이름 불일치, 분리/병합 제안 등을 표현한다.
- 전체 workspace에 직접 속하는 signal은 만들지 않는다.
- Signal의 소유자는 항상 문서 또는 폴더 중 하나다.

## 7. 폴더 책임 평가

- 폴더 책임 평가는 폴더가 자기 이름, 경로, 설명에 맞는 문서들을 담고 있는지 평가하는 것이다.
- 폴더 책임 평가는 폴더 추천, 폴더 정리 제안, 이상 문서 탐지에 사용된다.
- 책임 적합도, 설명과의 정렬, 문서 간 응집도, 이상 문서 여부는 폴더 signal로 표현한다.
- 폴더 책임 평가는 독립적인 최신 평가 결과로 관리하며, 과거 평가 이력은 보존하지 않는다.

## 8. 상태 관리

- source/index 계층은 작업 처리 상태를 소유하지 않는다.
- `pending`, `processing`, `failed`, `retry`, `locked` 같은 상태는 outbox, job queue, DLQ가 책임진다.
- source/index 계층은 삭제와 보존 정책만 표현한다.
- 삭제된 데이터는 일정 기간 보존한 뒤 정리할 수 있다.

## 9. Projection

- PostgreSQL은 최신 source, 최신 분석 결과, outbox event를 저장한다.
- Qdrant와 Neo4j 반영은 outbox worker가 비동기로 수행한다.
- Projection worker는 at-least-once delivery를 전제로 멱등해야 한다.
- 같은 이벤트가 여러 번 처리되어도 최종 결과는 한 번 처리한 것과 같아야 한다.
- 오래된 projection event는 최신 source와 비교해 무시한다.

## 10. Qdrant

- Qdrant는 의미 검색을 위한 vector projection 저장소다.
- Qdrant는 source of truth가 아니다.
- 문서, 폴더, chunk, signal은 모두 vector 검색 대상이 될 수 있다.
- 문서 signal과 폴더 signal은 모두 별도 signal vector로 저장할 수 있다.
- signal vector는 같은 signal collection 안에서 소유자가 문서인지 폴더인지 구분한다.
- 폴더 추천, 폴더 책임 평가, 이상 문서 탐지는 folder signal을 검색과 랭킹에 활용할 수 있어야 한다.

## 11. Neo4j

- Neo4j는 graph 탐색과 관계 기반 추천을 위한 projection 저장소다.
- Neo4j는 source of truth가 아니다.
- 문서, 폴더, signal 관계의 최신 graph projection만 유지한다.
- 문서 signal과 폴더 signal은 graph에서도 분리된 개념으로 다룬다.
- 폴더 signal이 특정 문서를 지목할 때만 해당 문서와 관계를 만든다.

## 12. 스키마 운영 원칙

- 현재 schema version은 계속 `1`이다.
- 현재 v1 스키마 자체를 최신 기준으로 유지한다.
- 점진 migration, legacy compatibility, dual-write, fallback query는 만들지 않는다.
- “나중에 필요할 수도 있음”만으로 테이블이나 컬럼을 추가하지 않는다.
- 필요한 구조라도 현재 책임이 명확하지 않으면 도입하지 않는다.
