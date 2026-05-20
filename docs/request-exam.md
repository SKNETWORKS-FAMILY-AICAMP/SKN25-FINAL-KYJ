# REQUEST_EXAM Task 요청 재검토 및 재작성

이 문서는 현재 코드 기준으로 App Server가 AI-Core Task API에 자연어 요청을 보낼 때 `REQUEST_EXAM`의 모든 요청을 다시 검토하고, Task로 보낼 수 있는 형태로 재작성한 결과다.
원문에 있던 표 row는 중복과 검증 설명문을 포함해 모두 유지했다. 이번 파일의 검토 대상 row 수는 `328`개다.

## 현재 Task 요청 계약

`POST /tasks`는 아래 형태를 받는다.

```json
{
  "tenant": "tenant-1",
  "request": "요청 본문",
  "context": {
    "requested_at": "2026-05-17T09:30:00+09:00",
    "document_id": "현재 문서 UUID",
    "folder_id": "현재 폴더 UUID"
  }
}
```

- `tenant`와 `request`는 필수다. `request`는 blank면 422다.
- `context`는 생략 가능하다. 생략하면 `requested_at`은 서버에서 현재 시각으로 보정된다.
- `context`를 보낼 때는 `requested_at`, `document_id`, `folder_id` 중 하나 이상이 있어야 한다. 빈 객체 `{}`는 422다.
- `context.requested_at`은 timezone-aware ISO timestamp여야 한다. naive timestamp는 422다.
- `context.document_id`와 `context.folder_id`는 UUID여야 한다.
- `POST /tasks/{task_id}/requests`는 기존 task에 요청을 추가한다. append context에 `document_id`/`folder_id`가 없으면 마지막 active request context를 상속한다.
- `DELETE /tasks/requests/{task_request_id}`는 request entry를 removed로 표시하고 active request로 다시 planning한다.
- 현재 Task HTTP DTO는 선택 텍스트, 원문 본문, 여러 문서 ID, project ID, folder hierarchy snapshot, document version scope, metadata list filter를 받지 않는다.

## 현재 Task 요청 플로우

1. `POST /tasks`: DTO 검증 -> `CreateTaskCommand` -> `RunTaskUseCase` -> `WorkflowRequestQueue.initial_snapshot` -> `TaskRepository.create` -> workflow planning/execution -> `TaskRepository.save` -> `TaskSnapshotResponse`.
2. `POST /tasks/{task_id}/requests`: 기존 task 조회 -> `WorkflowRequestQueue.append_request` -> active request text를 줄바꿈으로 병합 -> context 상속/갱신 -> workflow 재실행 -> 저장.
3. `DELETE /tasks/requests/{task_request_id}`: request entry 제거 표시 -> active request/context 재계산 -> active request가 남으면 workflow 재실행, 없으면 `Task has no active requests.`로 저장.
4. `POST /tasks/actions/result`: host action 결과 기록 -> checkpoint에서 workflow resume.

## 현재 planner/step 기준

- 검색/list: `find_documents -> present_documents`.
- 일반 질문: `find_documents -> answer_question(params.instruction)`.
- 문서 요약/정리: `find_documents -> summarize_documents(params.instruction)` 또는 현재 문서 요약의 경우 `find_signals(signal_type=summary) -> synthesize_signals`.
- 반복 이슈/고민: `find_signals(signal_type=issue) -> expand_signal_evidence(필요 시) -> synthesize_signals`.
- 결정사항/액션 아이템/약속: `find_signals(signal_type=commitment) -> expand_signal_evidence(필요 시) -> synthesize_signals`.
- 키워드/주제/개념/엔티티: `find_signals(signal_type=concept/entity) -> synthesize_signals`.
- 초안/재작성: `find_documents -> generate_draft(params.instruction)`. 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 붙을 수 있다.
- 아이디어 확장: `find_documents -> explore_ideas(params.instruction)`.
- 폴더 추천: `find_folders -> recommend_folder`. 단 Task HTTP DTO는 문서 본문 snapshot을 받지 않고, `recommend_folder`도 `context.document_id`로 원문을 조회하지 않는다.
- 현재 문서/폴더 요청은 planner가 `source_scope=current_document/current_folder`를 선택해야 `context.document_id/folder_id`가 검색 scope로 주입된다. context가 없으면 compiler가 `request_clarification` 한 step으로 바꾼다.
- signal vector 검색은 document/folder scope는 받지만 created_at/updated_at temporal scope를 지원하지 않는다. 따라서 “최근 결정사항/이번 주 할 일”처럼 signal 분석과 날짜 필터가 동시에 필요한 요청은 조건부다.

## 판단 기준

- `적절`: 현재 Task schema와 planner/step만으로 사용자-facing 결과를 비교적 안정적으로 만들 수 있다.
- `조건부 적절`: 비슷한 step은 있지만 source, scope, ranking, batch 대상, 선택 텍스트, 비교 대상, 날짜 signal scope, 또는 output 품질이 현재 retrieval/planner에 의존한다.
- `부적절`: 현재 Task API/step으로 핵심 입력 또는 출력 계약을 표현할 수 없어 별도 schema/use case/host action이 먼저 필요하다.

## 전체 요청 재작성 표

## 1. 문서 찾기 / 검색 요청

### 단순 검색

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 지난번에 작성한 회의록 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 내 문서 중에서 프로젝트 기획안 관련된 거 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| AI 관련해서 내가 쓴 문서들 보여줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 최근에 수정한 문서 알려줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 이번 달에 만든 문서만 모아서 보여줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 내가 작성한 문서 중 ‘마케팅’이라는 단어가 들어간 문서 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; exact contains/keyword-only mode가 없어 조건부다. |
| 제목은 기억 안 나는데, 고객 인터뷰 내용이 들어간 문서 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 지난주에 작성한 메모 중 중요한 것만 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 폴더 안 어딘가에 있는 계약서 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 내 문서 중에서 일정 관련 내용이 있는 문서 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
### 기억이 흐릿한 경우

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 예전에 스타트업 아이디어에 대해 정리한 문서가 있었는데 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 언젠가 서비스 개선점에 대해 쓴 글이 있었는데 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 이름은 기억 안 나는데, 사용자 피드백을 정리한 문서를 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 내가 예전에 독서 기록처럼 적어둔 문서 있으면 보여줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 대충 ‘문제점’이랑 ‘해결책’ 같은 내용이 있던 문서 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; exact contains/keyword-only mode가 없어 조건부다. |
| 내가 작성한 문서 중 투자 유치랑 관련 있을 것 같은 문서 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
### 의미 기반 검색

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 내 문서 중에서 수익 모델과 관련된 내용을 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 고객 pain point에 해당하는 내용들을 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 사업화 가능성이 높은 아이디어 문서를 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 내가 적은 내용 중 실행 계획으로 바꿀 수 있는 것들을 찾아줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 기술적으로 구현이 어려울 것 같은 내용이 있는 문서를 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 내 문서에서 반복적으로 등장하는 고민이나 문제를 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
## 2. 문서 요약 요청

### 단일 문서 요약

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이 문서 핵심만 요약해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서를 세 줄로 요약해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서를 회의 공유용으로 요약해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서에서 결론만 뽑아줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서를 읽기 쉽게 정리해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서에서 중요한 부분만 bullet로 정리해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서의 목적, 핵심 내용, 다음 행동으로 나눠서 요약해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
### 여러 문서 요약

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이 폴더 안 문서들을 전체적으로 요약해줘. | `request`는 원문 그대로, `context.folder_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_folder`, `find_documents -> summarize_documents/answer_question`; `context.folder_id` 누락 시 `request_clarification`. |
| 최근 작성한 문서들의 공통 내용을 요약해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 프로젝트 관련 문서들을 한 번에 요약해줘. | 프로젝트가 폴더라면 `context.folder_id`를 붙여 현재 폴더 요청으로 바꾸고, 아니면 프로젝트명을 request에 명시한다. | 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 회의록들을 모아서 주요 결정사항만 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_signals(signal_type=commitment) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 내 아이디어 문서들을 묶어서 핵심 주제별로 요약해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_signals(signal_type=concept/entity) -> synthesize_signals`. |
| 고객 인터뷰 문서들을 종합해서 인사이트를 뽑아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
### 특정 관점 요약

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이 문서를 개발자 관점에서 요약해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서를 기획자 관점에서 요약해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서를 투자자에게 설명한다고 생각하고 요약해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서를 발표 자료로 만들 수 있게 요약해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서에서 리스크만 뽑아줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서에서 장점과 단점을 나눠서 정리해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서에서 실행해야 할 일만 추려줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
## 3. 폴더 정리 요청

### 폴더 추천

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이 문서를 어느 폴더에 넣으면 좋을지 추천해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 조건부 적절 | `find_folders -> recommend_folder`; 단 `recommend_folder`는 `context.document_id`로 문서 snapshot을 조회하지 않는다. |
| 이 문서에 어울리는 폴더를 찾아줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 조건부 적절 | `find_folders -> recommend_folder`; 단 `recommend_folder`는 `context.document_id`로 문서 snapshot을 조회하지 않는다. |
| 내 폴더 중 이 문서와 가장 관련 있는 곳을 추천해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 조건부 적절 | `find_folders -> recommend_folder`; 단 `recommend_folder`는 `context.document_id`로 문서 snapshot을 조회하지 않는다. |
| 이 문서는 새 폴더를 만드는 게 좋을까, 기존 폴더에 넣는 게 좋을까? | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 조건부 적절 | `find_folders -> recommend_folder`; 단 `recommend_folder`는 `context.document_id`로 문서 snapshot을 조회하지 않는다. |
| 이 문서와 비슷한 문서들이 들어있는 폴더를 찾아줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 조건부 적절 | `source_scope=current_document`는 가능하지만 related anchor/exclude-current-doc 처리가 고정되어 있지 않다. |
### 폴더 구조 개선

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 내 폴더 구조가 너무 복잡한데 정리 방향을 추천해줘. | 폴더 구조 조회/변경 전용 API 또는 host action schema를 만든 뒤 별도 요청으로 보낸다. | 부적절 | 현재 action은 `find_folders -> recommend_folder` 수준이며 hierarchy/rename/merge/restructure action이 없다. |
| 비슷한 폴더가 있으면 합칠 만한 것들을 알려줘. | 폴더 구조 조회/변경 전용 API 또는 host action schema를 만든 뒤 별도 요청으로 보낸다. | 부적절 | 현재 action은 `find_folders -> recommend_folder` 수준이며 hierarchy/rename/merge/restructure action이 없다. |
| 폴더 이름이 애매한 것들을 더 명확하게 바꿔줘. | 폴더 구조 조회/변경 전용 API 또는 host action schema를 만든 뒤 별도 요청으로 보낸다. | 부적절 | 현재 action은 `find_folders -> recommend_folder` 수준이며 hierarchy/rename/merge/restructure action이 없다. |
| 내 문서들을 기준으로 폴더 구조를 다시 설계해줘. | 폴더 구조 조회/변경 전용 API 또는 host action schema를 만든 뒤 별도 요청으로 보낸다. | 부적절 | 현재 action은 `find_folders -> recommend_folder` 수준이며 hierarchy/rename/merge/restructure action이 없다. |
| 중복되거나 겹치는 폴더를 찾아줘. | 폴더 구조 조회/변경 전용 API 또는 host action schema를 만든 뒤 별도 요청으로 보낸다. | 부적절 | 현재 action은 `find_folders -> recommend_folder` 수준이며 hierarchy/rename/merge/restructure action이 없다. |
| 내 폴더들을 주제별로 다시 분류해줘. | 폴더 구조 조회/변경 전용 API 또는 host action schema를 만든 뒤 별도 요청으로 보낸다. | 부적절 | 현재 action은 `find_folders -> recommend_folder` 수준이며 hierarchy/rename/merge/restructure action이 없다. |
| 폴더가 너무 많아졌는데 상위 카테고리로 묶어줘. | 폴더 구조 조회/변경 전용 API 또는 host action schema를 만든 뒤 별도 요청으로 보낸다. | 부적절 | 현재 action은 `find_folders -> recommend_folder` 수준이며 hierarchy/rename/merge/restructure action이 없다. |
### 자동 분류 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 정리되지 않은 문서들을 적절한 폴더로 분류해줘. | 문서 상태/메타데이터 목록 필터를 받는 전용 list/review use case가 먼저 필요하다. | 부적절 | Task request에는 metadata/list filter와 상태 기반 batch 대상 지정이 없다. |
| 최근 만든 문서들을 알맞은 폴더에 넣을 수 있게 추천해줘. | `request`는 원문 그대로 보낼 수 있으나, 현재 문서 본문 snapshot을 Task가 받지 못해 추천 품질은 제한된다. | 조건부 적절 | `find_folders -> recommend_folder`; 단 `recommend_folder`는 `context.document_id`로 문서 snapshot을 조회하지 않는다. |
| 폴더 없는 문서들을 정리해줘. | 문서 상태/메타데이터 목록 필터를 받는 전용 list/review use case가 먼저 필요하다. | 부적절 | Task request에는 metadata/list filter와 상태 기반 batch 대상 지정이 없다. |
| 내 문서들을 업무, 개인, 아이디어, 학습으로 나눠줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents(require_comprehensive_search=true) -> classify_documents -> analyze_documents -> synthesize_report`로 시도할 수 있지만 전체 문서 순회/고정된 batch 대상은 없다. |
| 중요한 문서와 임시 문서를 구분해줘. | 문서 상태/메타데이터 목록 필터를 받는 전용 list/review use case가 먼저 필요하다. | 부적절 | Task request에는 metadata/list filter와 상태 기반 batch 대상 지정이 없다. |
| 오래된 문서 중 보관용으로 옮길 만한 것들을 찾아줘. | 문서 상태/메타데이터 목록 필터를 받는 전용 list/review use case가 먼저 필요하다. | 부적절 | Task request에는 metadata/list filter와 상태 기반 batch 대상 지정이 없다. |
## 4. 관련 문서 추천 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이 문서와 관련 있는 다른 문서를 찾아줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 조건부 적절 | `source_scope=current_document`는 가능하지만 related anchor/exclude-current-doc 처리가 고정되어 있지 않다. |
| 현재 보고 있는 문서와 비슷한 문서를 추천해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 조건부 적절 | `source_scope=current_document`는 가능하지만 related anchor/exclude-current-doc 처리가 고정되어 있지 않다. |
| 이 아이디어와 연결될 만한 과거 메모를 찾아줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 이 회의록과 관련된 이전 회의록을 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 이 프로젝트와 연결된 자료들을 모아줘. | 프로젝트가 폴더라면 `context.folder_id`를 붙여 현재 폴더 요청으로 바꾸고, 아니면 프로젝트명을 request에 명시한다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 이 문서에서 언급한 내용과 비슷한 문서가 있는지 찾아줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 조건부 적절 | `source_scope=current_document`는 가능하지만 related anchor/exclude-current-doc 처리가 고정되어 있지 않다. |
| 내가 예전에 비슷한 고민을 적어둔 문서가 있는지 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 이 문서를 보완할 수 있는 참고 문서를 찾아줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 조건부 적절 | `source_scope=current_document`는 가능하지만 related anchor/exclude-current-doc 처리가 고정되어 있지 않다. |
| 이 내용과 충돌하거나 반대되는 내용이 있는 문서를 찾아줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 이 문서와 같은 주제인데 더 자세한 문서를 찾아줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 조건부 적절 | `source_scope=current_document`는 가능하지만 related anchor/exclude-current-doc 처리가 고정되어 있지 않다. |
## 5. 질문 답변 요청

### 전체 문서 기반 질문

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 내 문서들을 보면 지금 진행 중인 프로젝트가 뭐야? | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 내가 가장 많이 고민한 주제는 뭐야? | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=issue) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 내 문서들에서 자주 나오는 키워드를 알려줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=concept/entity) -> synthesize_signals`. |
| 내가 최근에 집중하고 있는 일은 뭐야? | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 내 문서들을 기준으로 내가 해야 할 일을 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=commitment) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 내가 작성한 내용 중 아직 해결되지 않은 문제가 뭐야? | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=issue) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
### 특정 문서 기반 질문

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이 문서에서 핵심 문제는 뭐야? | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서에서 말하는 해결책은 뭐야? | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서에 빠진 내용은 뭐야? | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서에서 모호한 부분을 알려줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서의 논리 흐름이 자연스러운지 봐줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서에서 더 구체화해야 할 부분을 알려줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
### 비교 질문

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이 문서와 저 문서의 차이점을 알려줘. | `selected_document_ids` 또는 version scope가 생긴 뒤 비교 요청으로 보낸다. | 부적절 | Task request에는 비교 대상 문서 ID 목록이나 version scope가 없다. |
| 두 기획안 중 어떤 게 더 현실적이야? | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> answer_question`로 시도는 가능하지만 비교 대상 고정이 retrieval에 의존한다. |
| 이전 버전과 지금 버전의 핵심 차이를 설명해줘. | `selected_document_ids` 또는 version scope가 생긴 뒤 비교 요청으로 보낸다. | 부적절 | Task request에는 비교 대상 문서 ID 목록이나 version scope가 없다. |
| A 프로젝트와 B 프로젝트의 공통점을 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`로 시도는 가능하지만 비교 대상 고정이 retrieval에 의존한다. |
| 이 두 문서가 서로 충돌하는 내용이 있는지 확인해줘. | `selected_document_ids` 또는 version scope가 생긴 뒤 비교 요청으로 보낸다. | 부적절 | Task request에는 비교 대상 문서 ID 목록이나 version scope가 없다. |
| 비슷한 내용이 중복되어 있는 문서를 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
## 6. 문서 작성 보조 요청

### 초안 작성

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이 아이디어를 바탕으로 기획안 초안을 작성해줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> generate_draft`; 선택 아이디어 본문을 Task schema가 직접 받지 못해 source 고정은 조건부다. |
| 이 메모를 보고 정식 문서로 만들어줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 회의 내용을 바탕으로 회의록을 작성해줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 내가 적은 키워드들로 문서 초안을 만들어줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> generate_draft`; 키워드 원문을 Task context로 직접 전달하는 필드는 없다. |
| 이 내용을 보고 제안서 형태로 정리해줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 이 문서를 블로그 글처럼 바꿔줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> generate_draft/answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 내용을 발표 스크립트로 만들어줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
### 문서 개선

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이 문서를 더 읽기 쉽게 다듬어줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> generate_draft/answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 문장 표현을 자연스럽게 바꿔줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 중복된 내용을 줄여줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 논리 흐름을 더 명확하게 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 제목과 소제목을 붙여줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 내용 순서를 다시 구성해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 너무 긴 문장을 짧게 바꿔줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 전문적인 느낌으로 다듬어줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 덜 딱딱하고 자연스럽게 바꿔줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
### 형식 변환

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이 문서를 보고 발표 자료 목차로 바꿔줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> generate_draft/answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 내용을 체크리스트로 만들어줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 이 문서를 표 형태로 정리해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 이 내용을 할 일 목록으로 바꿔줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_signals(signal_type=commitment) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 이 문서를 보고 이메일 초안을 만들어줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> generate_draft/answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 내용을 회의 아젠다로 바꿔줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 이 문서를 보고 보고서 형식으로 다시 작성해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> generate_draft/answer_question`; `context.document_id` 누락 시 `request_clarification`. |
## 7. 아이디어 발전 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이 아이디어를 더 구체화해줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> explore_ideas/answer_question`; 선택 본문이 없으면 검색 evidence에 의존한다. |
| 이 아이디어의 장단점을 분석해줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> explore_ideas/answer_question`; 선택 본문이 없으면 검색 evidence에 의존한다. |
| 이 아이디어를 사업화하려면 무엇이 필요해? | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> explore_ideas/answer_question`; 선택 본문이 없으면 검색 evidence에 의존한다. |
| 이 아이디어와 관련된 기존 문서를 찾아서 함께 정리해줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> explore_ideas/answer_question`; 선택 본문이 없으면 검색 evidence에 의존한다. |
| 이 아이디어에서 부족한 부분을 알려줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_signals(signal_type=issue) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 이 아이디어를 MVP 수준으로 줄여줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> explore_ideas/answer_question`; 선택 본문이 없으면 검색 evidence에 의존한다. |
| 이 아이디어를 사용자 문제 중심으로 다시 정리해줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_signals(signal_type=issue) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 이 아이디어를 실제 기능 목록으로 바꿔줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> explore_ideas/answer_question`; 선택 본문이 없으면 검색 evidence에 의존한다. |
| 이 아이디어를 실행 가능한 계획으로 만들어줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> explore_ideas/answer_question`; 선택 본문이 없으면 검색 evidence에 의존한다. |
| 비슷한 아이디어끼리 묶어줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> explore_ideas/answer_question`; 선택 본문이 없으면 검색 evidence에 의존한다. |
| 내 아이디어 문서들 중 가장 발전 가능성이 높은 걸 골라줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> explore_ideas/answer_question`; 선택 본문이 없으면 검색 evidence에 의존한다. |
## 8. 실행 계획 / 액션 아이템 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이 문서 내용을 바탕으로 해야 할 일을 정리해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 다음 액션 아이템을 뽑아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=commitment) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 우선순위별로 할 일을 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=commitment) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 이번 주에 해야 할 일만 추려줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=commitment) -> synthesize_signals`가 의도된 경로지만 signal vector scope는 created_at/updated_at 필터를 지원하지 않아 날짜 조건은 조건부다. |
| 이 프로젝트를 진행하려면 단계별로 뭘 해야 해? | 프로젝트가 폴더라면 `context.folder_id`를 붙여 현재 폴더 요청으로 바꾸고, 아니면 프로젝트명을 request에 명시한다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 이 문서에서 미뤄진 작업들을 찾아줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 회의록에서 담당자와 할 일을 분리해서 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=commitment) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 실행 가능한 작업과 아직 고민이 필요한 내용을 나눠줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=issue) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 이 계획에서 먼저 해야 할 일 3개만 알려줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_signals(signal_type=commitment) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 내 문서들을 보고 지금 당장 처리해야 할 일을 추천해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=commitment) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
## 9. 회고 / 분석 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 내 문서들을 보면 내가 어떤 방향으로 생각이 바뀌었는지 알려줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=concept/entity) -> synthesize_signals`. |
| 최근 한 달간 작성한 문서를 바탕으로 회고를 작성해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 내가 반복해서 미루는 일이 있는지 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 내가 자주 언급하는 문제를 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=issue) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 내 문서에서 계속 반복되는 키워드를 분석해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=concept/entity) -> synthesize_signals`. |
| 내가 예전에는 중요하게 봤지만 최근에는 덜 언급하는 주제가 뭐야? | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=concept) -> synthesize_signals`가 의도된 경로지만 날짜 scope는 signal 검색에서 제한된다. |
| 내가 진행 중인 프로젝트들의 상태를 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 완료된 일과 아직 남은 일을 구분해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=commitment) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 내 기록을 바탕으로 이번 달 성과를 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 내 문서들을 보고 앞으로 집중해야 할 방향을 추천해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=concept/entity) -> synthesize_signals`. |
## 10. 중복 / 충돌 / 누락 확인 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 비슷한 내용의 문서가 중복되어 있는지 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 같은 주제를 다루는 문서들을 묶어줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=concept/entity) -> synthesize_signals`. |
| 서로 내용이 충돌하는 문서를 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 이 문서에서 빠진 내용이 있는지 알려줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 계획에서 현실성이 부족한 부분을 찾아줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 이 문서에 근거가 부족한 주장을 찾아줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서와 관련된 자료가 더 필요한 부분을 알려줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 조건부 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 내가 같은 내용을 여러 번 적은 문서가 있는지 확인해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 오래된 정보가 들어있는 문서를 찾아줘. | 현재 Task schema로는 핵심 입력을 표현할 수 없어 전용 schema/use case가 먼저 필요하다. | 부적절 | 현재 workflow step으로 핵심 입력이나 출력 계약을 안정적으로 만들 수 없다. |
| 현재 문서 구조에서 빈틈이 있는 부분을 알려줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
## 11. 이름 / 제목 / 태그 추천 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이 문서 제목을 추천해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 폴더 이름을 더 명확하게 바꿔줘. | 현재 Task schema로는 핵심 입력을 표현할 수 없어 전용 schema/use case가 먼저 필요하다. | 부적절 | 현재 workflow step으로 핵심 입력이나 출력 계약을 안정적으로 만들 수 없다. |
| 이 문서에 어울리는 키워드를 추천해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서를 분류하기 좋은 태그를 추천해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 이 폴더 안 문서들을 보고 폴더 이름을 다시 지어줘. | 현재 Task schema로는 핵심 입력을 표현할 수 없어 전용 schema/use case가 먼저 필요하다. | 부적절 | 현재 workflow step으로 핵심 입력이나 출력 계약을 안정적으로 만들 수 없다. |
| 비슷한 문서들을 묶을 수 있는 카테고리 이름을 추천해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 이 문서의 핵심 주제를 한 단어로 표현해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 문서 제목이 너무 애매한 것들을 찾아서 개선안을 줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 내 폴더 이름들을 더 일관성 있게 정리해줘. | 현재 Task schema로는 핵심 입력을 표현할 수 없어 전용 schema/use case가 먼저 필요하다. | 부적절 | 현재 workflow step으로 핵심 입력이나 출력 계약을 안정적으로 만들 수 없다. |
## 12. 지식 정리 / 구조화 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 내 문서들을 지식 베이스처럼 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 이 폴더 내용을 주제별로 정리해줘. | `request`는 원문 그대로, `context.folder_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_folder`, `find_documents -> summarize_documents/answer_question`; `context.folder_id` 누락 시 `request_clarification`. |
| 내가 정리한 내용들을 개념 지도처럼 연결해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=concept/entity) -> synthesize_signals`. |
| 이 문서에서 핵심 개념과 세부 개념을 나눠줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 주제와 관련된 문서들을 계층 구조로 정리해줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_signals(signal_type=concept/entity) -> synthesize_signals`. |
| 내 문서들을 공부 노트처럼 재구성해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 이 내용을 초보자도 이해할 수 있게 다시 정리해줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 내 문서들에서 개념, 예시, 할 일, 참고자료를 분리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=commitment) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 문서들을 기반으로 FAQ를 만들어줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 이 폴더 안 내용을 하나의 가이드 문서로 통합해줘. | `request`는 원문 그대로, `context.folder_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_folder`, `find_documents -> generate_draft`; `context.folder_id` 누락 시 `request_clarification`. |
## 13. 회의록 관련 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 회의록에서 결정사항만 뽑아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=commitment) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 회의록에서 할 일만 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=commitment) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 회의록을 참석자별 액션 아이템으로 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=commitment) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 회의록을 짧게 요약해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 회의록에서 논의만 되고 결정되지 않은 내용을 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 지난 회의록들과 비교해서 새로 추가된 내용을 알려줘. | `selected_document_ids` 또는 version scope가 생긴 뒤 비교 요청으로 보낸다. | 부적절 | Task request에는 비교 대상 문서 ID 목록이나 version scope가 없다. |
| 회의록을 보고 다음 회의 아젠다를 만들어줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 회의록에 빠진 내용이 있는지 확인해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=issue) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 회의록을 보고 프로젝트 진행 상태를 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 회의록 내용 중 중요한 부분을 강조해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
## 14. 프로젝트 관리 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이 프로젝트 관련 문서들을 모두 모아줘. | 프로젝트가 폴더라면 `context.folder_id`를 붙여 현재 폴더 요청으로 바꾸고, 아니면 프로젝트명을 request에 명시한다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 이 프로젝트의 현재 상태를 정리해줘. | 프로젝트가 폴더라면 `context.folder_id`를 붙여 현재 폴더 요청으로 바꾸고, 아니면 프로젝트명을 request에 명시한다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 이 프로젝트에서 아직 남은 일을 알려줘. | 프로젝트가 폴더라면 `context.folder_id`를 붙여 현재 폴더 요청으로 바꾸고, 아니면 프로젝트명을 request에 명시한다. | 조건부 적절 | `find_signals(signal_type=commitment) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 이 프로젝트의 리스크를 정리해줘. | 프로젝트가 폴더라면 `context.folder_id`를 붙여 현재 폴더 요청으로 바꾸고, 아니면 프로젝트명을 request에 명시한다. | 조건부 적절 | `find_signals(signal_type=issue) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 이 프로젝트 관련 회의록과 기획서를 연결해서 보여줘. | 프로젝트가 폴더라면 `context.folder_id`를 붙여 현재 폴더 요청으로 바꾸고, 아니면 프로젝트명을 request에 명시한다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 이 프로젝트의 전체 히스토리를 요약해줘. | 프로젝트가 폴더라면 `context.folder_id`를 붙여 현재 폴더 요청으로 바꾸고, 아니면 프로젝트명을 request에 명시한다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 이 프로젝트를 단계별 계획으로 정리해줘. | 프로젝트가 폴더라면 `context.folder_id`를 붙여 현재 폴더 요청으로 바꾸고, 아니면 프로젝트명을 request에 명시한다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 이 프로젝트에서 결정된 사항과 미정인 사항을 나눠줘. | 프로젝트가 폴더라면 `context.folder_id`를 붙여 현재 폴더 요청으로 바꾸고, 아니면 프로젝트명을 request에 명시한다. | 조건부 적절 | `find_signals(signal_type=commitment) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 프로젝트별로 문서를 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 내 문서들을 보고 현재 진행 중인 프로젝트 목록을 만들어줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=concept/entity) -> synthesize_signals`. |
## 15. 개인 메모 / 일상 기록 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 최근 내 메모를 보고 관심사를 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=concept) -> synthesize_signals`가 의도된 경로지만 날짜 scope는 signal 검색에서 제한된다. |
| 내가 요즘 고민하는 게 뭔지 알려줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=issue) -> synthesize_signals`가 의도된 경로지만 날짜 scope는 signal 검색에서 제한된다. |
| 내 일상 기록을 바탕으로 이번 주 회고를 써줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 내 메모에서 반복되는 감정이나 생각을 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 내가 적어둔 아이디어 중 실천 가능한 것을 골라줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> explore_ideas/answer_question`; 선택 본문이 없으면 검색 evidence에 의존한다. |
| 개인 메모와 업무 메모를 구분해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 내 기록 중 나중에 다시 봐야 할 내용을 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 내 메모에서 일정이나 약속처럼 보이는 내용을 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 내가 적어둔 목표들을 모아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 내 기록을 바탕으로 다음 달 목표를 추천해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=concept/entity) -> synthesize_signals`. |
## 16. 학습 / 공부 문서 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 내 공부 노트들을 주제별로 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=concept/entity) -> synthesize_signals`. |
| 이 개념을 내가 적은 문서 기준으로 설명해줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_signals(signal_type=concept/entity) -> synthesize_signals`. |
| 내가 정리한 내용 중 이해가 부족해 보이는 부분을 알려줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=issue) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 학습 문서들을 난이도 순으로 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 내 노트를 바탕으로 복습 문제를 만들어줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=issue) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 이 폴더 안 내용을 시험 대비용 요약본으로 만들어줘. | `request`는 원문 그대로, `context.folder_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_folder`, `find_documents -> generate_draft`; `context.folder_id` 누락 시 `request_clarification`. |
| 내가 자주 헷갈리는 개념을 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 공부한 내용을 개념별로 다시 묶어줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=concept/entity) -> synthesize_signals`. |
| 이 문서를 플래시카드 형태로 바꿔줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> generate_draft/answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 내 학습 기록을 보고 다음에 공부할 내용을 추천해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
## 17. 문서 품질 평가 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이 문서가 잘 정리되어 있는지 평가해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서에서 설득력이 부족한 부분을 알려줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서의 논리적 약점을 찾아줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서가 너무 추상적인 부분을 찾아줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 더 구체적인 예시가 필요한 부분을 알려줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 이 문서의 가독성을 높이려면 어떻게 해야 해? | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서에서 불필요한 내용을 줄여줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서의 핵심 메시지가 잘 드러나는지 봐줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서를 더 전문적으로 보이게 다듬어줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> generate_draft/answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 문서를 다른 사람이 읽어도 이해할 수 있을지 평가해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
## 18. 통합 / 병합 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 비슷한 문서들을 하나로 합쳐줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 이 두 문서를 자연스럽게 합쳐줘. | `selected_document_ids` 또는 version scope가 생긴 뒤 비교 요청으로 보낸다. | 부적절 | Task request에는 비교 대상 문서 ID 목록이나 version scope가 없다. |
| 여러 메모를 하나의 정리 문서로 만들어줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 회의록과 기획안을 합쳐서 실행 계획 문서로 만들어줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 이 폴더 안 문서들을 하나의 최종본으로 정리해줘. | `request`는 원문 그대로, `context.folder_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_folder`, `find_documents -> generate_draft`; `context.folder_id` 누락 시 `request_clarification`. |
| 중복 내용은 제거하고 핵심만 남겨줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 여러 아이디어 문서를 하나의 사업 기획안으로 합쳐줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> generate_draft`; 합칠 문서 집합은 retrieval 후보에 의존한다. |
| 관련 문서들을 묶어서 하나의 보고서 초안으로 만들어줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 이 문서들을 연결해서 흐름이 있는 글로 만들어줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 조건부 적절 | `source_scope=current_document`, `find_documents -> generate_draft/answer_question`; `context.document_id` 누락 시 `request_clarification`. |
## 19. 정리되지 않은 자료 처리 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 임시 문서들을 정리해줘. | 문서 상태/메타데이터 목록 필터를 받는 전용 list/review use case가 먼저 필요하다. | 부적절 | Task request에는 metadata/list filter와 상태 기반 batch 대상 지정이 없다. |
| 제목 없는 문서들에 제목을 붙여줘. | 문서 상태/메타데이터 목록 필터를 받는 전용 list/review use case가 먼저 필요하다. | 부적절 | Task request에는 metadata/list filter와 상태 기반 batch 대상 지정이 없다. |
| 내용이 거의 없는 문서를 찾아줘. | 문서 상태/메타데이터 목록 필터를 받는 전용 list/review use case가 먼저 필요하다. | 부적절 | Task request에는 metadata/list filter와 상태 기반 batch 대상 지정이 없다. |
| 정리가 필요한 문서들을 알려줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 오래 방치된 문서를 찾아줘. | 문서 상태/메타데이터 목록 필터를 받는 전용 list/review use case가 먼저 필요하다. | 부적절 | Task request에는 metadata/list filter와 상태 기반 batch 대상 지정이 없다. |
| 나중에 봐야 할 문서와 삭제해도 될 문서를 구분해줘. | 문서 상태/메타데이터 목록 필터를 받는 전용 list/review use case가 먼저 필요하다. | 부적절 | Task request에는 metadata/list filter와 상태 기반 batch 대상 지정이 없다. |
| 폴더에 안 들어간 문서들을 정리해줘. | 문서 상태/메타데이터 목록 필터를 받는 전용 list/review use case가 먼저 필요하다. | 부적절 | Task request에는 metadata/list filter와 상태 기반 batch 대상 지정이 없다. |
| 최근 작성했지만 정리 안 된 문서들을 보여줘. | 현재 Task schema로는 핵심 입력을 표현할 수 없어 전용 schema/use case가 먼저 필요하다. | 부적절 | 현재 workflow step으로 핵심 입력이나 출력 계약을 안정적으로 만들 수 없다. |
| 내 문서 중 초안 상태인 것들을 찾아줘. | 문서 상태/메타데이터 목록 필터를 받는 전용 list/review use case가 먼저 필요하다. | 부적절 | Task request에는 metadata/list filter와 상태 기반 batch 대상 지정이 없다. |
| 완성도가 높은 문서와 낮은 문서를 구분해줘. | 문서 상태/메타데이터 목록 필터를 받는 전용 list/review use case가 먼저 필요하다. | 부적절 | Task request에는 metadata/list filter와 상태 기반 batch 대상 지정이 없다. |
## 20. 자연어 명령형 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 내 문서 좀 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 이거 어디에 넣어야 할지 알려줘. | `request`는 원문 그대로 보낼 수 있으나, 현재 문서 본문 snapshot을 Task가 받지 못해 추천 품질은 제한된다. | 조건부 적절 | `find_folders -> recommend_folder`; 단 `recommend_folder`는 `context.document_id`로 문서 snapshot을 조회하지 않는다. |
| 중요한 것만 뽑아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 나중에 다시 볼 만한 것들만 모아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 이 내용 기반으로 다음에 뭘 해야 할지 알려줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 내가 뭘 하려고 했는지 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 이 문서랑 관련된 것들 다 찾아줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 조건부 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 흩어진 내용들을 하나로 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 내 생각을 좀 구조화해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 이걸 더 쓸모 있는 문서로 만들어줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
## 21. 사용자 입장에서 매우 현실적인 모호한 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이거 정리해줘. | App Server가 UI 대상에 맞춰 현재 문서/폴더 요청으로 풀어 쓰고 해당 context id를 붙인다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 이거 뭔 내용이야? | App Server가 UI 대상에 맞춰 현재 문서/폴더 요청으로 풀어 쓰고 해당 context id를 붙인다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 이거 중요한 거야? | App Server가 UI 대상에 맞춰 현재 문서/폴더 요청으로 풀어 쓰고 해당 context id를 붙인다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 이거 어디에 둬야 해? | `request`는 원문 그대로 보낼 수 있으나, 현재 문서 본문 snapshot을 Task가 받지 못해 추천 품질은 제한된다. | 조건부 적절 | `find_folders -> recommend_folder`; 단 `recommend_folder`는 `context.document_id`로 문서 snapshot을 조회하지 않는다. |
| 비슷한 거 또 있어? | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 전에 이런 거 쓴 적 있지 않아? | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 내가 이거 왜 적었을까? | App Server가 UI 대상에 맞춰 현재 문서/폴더 요청으로 풀어 쓰고 해당 context id를 붙인다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 이거 다음에 뭐 해야 하지? | App Server가 UI 대상에 맞춰 현재 문서/폴더 요청으로 풀어 쓰고 해당 context id를 붙인다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 이거 좀 보기 좋게 바꿔줘. | App Server가 UI 대상에 맞춰 현재 문서/폴더 요청으로 풀어 쓰고 해당 context id를 붙인다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 이거 나중에 찾기 쉽게 해줘. | App Server가 UI 대상에 맞춰 현재 문서/폴더 요청으로 풀어 쓰고 해당 context id를 붙인다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 이 문서 너무 복잡한데 쉽게 바꿔줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> generate_draft/answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이거랑 관련된 자료 다 모아줘. | App Server가 UI 대상에 맞춰 현재 문서/폴더 요청으로 풀어 쓰고 해당 context id를 붙인다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
## 22. 고급 사용자처럼 보이지만 여전히 스키마를 모르는 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 내 문서들을 의미적으로 비슷한 것끼리 클러스터링해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 내 지식 베이스에서 이 주제와 가장 가까운 문서들을 찾아줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 최근 문서들을 기반으로 관심사 변화를 분석해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=concept) -> synthesize_signals`가 의도된 경로지만 날짜 scope는 signal 검색에서 제한된다. |
| 내 폴더 구조가 실제 문서 내용과 잘 맞는지 평가해줘. | 현재 Task schema로는 핵심 입력을 표현할 수 없어 전용 schema/use case가 먼저 필요하다. | 부적절 | 현재 workflow step으로 핵심 입력이나 출력 계약을 안정적으로 만들 수 없다. |
| 문서 간 관계를 기반으로 추천 구조를 만들어줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 내 문서 전체에서 반복되는 문제-해결 패턴을 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 이 문서가 어떤 기존 맥락과 연결되는지 설명해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 조건부 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 내 기록을 바탕으로 장기 목표와 단기 목표를 구분해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=concept/entity) -> synthesize_signals`. |
| 내 문서들을 기반으로 지식 그래프처럼 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 내가 쌓아둔 자료 중 활용도가 높은 것부터 추천해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
## 23. AI에게 실제로 기대할 수 있는 복합 요청

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 최근 작성한 프로젝트 문서들을 찾아서 요약하고, 해야 할 일을 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=commitment) -> synthesize_signals`가 의도된 경로지만 signal vector scope는 created_at/updated_at 필터를 지원하지 않아 날짜 조건은 조건부다. |
| 이 문서를 분석해서 적절한 폴더를 추천하고, 비슷한 문서도 같이 보여줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 조건부 적절 | `source_scope=current_document`는 가능하지만 related anchor/exclude-current-doc 처리가 고정되어 있지 않다. |
| 내 아이디어 문서들을 모아서 사업화 가능성이 높은 순서로 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> explore_ideas/answer_question`; 선택 본문이 없으면 검색 evidence에 의존한다. |
| 회의록들을 분석해서 결정사항, 미정사항, 액션 아이템으로 나눠줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_signals(signal_type=commitment) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 정리되지 않은 문서들을 찾아서 폴더 추천까지 해줘. | 문서 상태/메타데이터 목록 필터를 받는 전용 list/review use case가 먼저 필요하다. | 부적절 | Task request에는 metadata/list filter와 상태 기반 batch 대상 지정이 없다. |
| 이 폴더 안 문서들을 하나의 보고서 초안으로 만들어줘. | `request`는 원문 그대로, `context.folder_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_folder`, `find_documents -> generate_draft`; `context.folder_id` 누락 시 `request_clarification`. |
| 내 문서들을 보고 이번 주에 집중해야 할 일을 추천해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=commitment) -> synthesize_signals`가 의도된 경로지만 signal vector scope는 created_at/updated_at 필터를 지원하지 않아 날짜 조건은 조건부다. |
| 내가 적어둔 목표와 실제 진행 문서를 비교해서 부족한 부분을 알려줘. | `selected_document_ids` 또는 version scope가 생긴 뒤 비교 요청으로 보낸다. | 부적절 | Task request에는 비교 대상 문서 ID 목록이나 version scope가 없다. |
| 비슷한 문서들을 묶고 중복 내용을 제거해서 최종 정리본을 만들어줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 내 전체 문서에서 중요한 주제들을 뽑고, 각 주제별 대표 문서를 추천해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> recommend_documents`; anchor나 제외 대상이 필요하면 현재 schema로는 조건부다. |
## 24. 서비스 AI 기능 검증에 좋은 요청 세트

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 아래 요청들은 실제 AI 기능을 테스트하기에 좋다. | Task request가 아니라 검증 설명문이므로 전송하지 않는다. | 부적절 | workflow action으로 매핑하지 않는다. |
### 검색 능력 테스트

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 제목은 기억 안 나는데, 고객 인터뷰 내용이 들어간 문서 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 내가 예전에 수익 모델에 대해 쓴 문서 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 이 문서와 관련 있는 과거 문서를 찾아줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 조건부 적절 | `source_scope=current_document`는 가능하지만 related anchor/exclude-current-doc 처리가 고정되어 있지 않다. |
### 요약 능력 테스트

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이 폴더 안 문서들을 핵심만 요약해줘. | `request`는 원문 그대로, `context.folder_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_folder`, `find_documents -> summarize_documents/answer_question`; `context.folder_id` 누락 시 `request_clarification`. |
| 최근 회의록들을 종합해서 결정사항만 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=commitment) -> synthesize_signals`가 의도된 경로지만 signal vector scope는 created_at/updated_at 필터를 지원하지 않아 날짜 조건은 조건부다. |
| 이 문서를 세 줄로 요약해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
### 추천 능력 테스트

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이 문서를 어느 폴더에 넣으면 좋을지 추천해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 조건부 적절 | `find_folders -> recommend_folder`; 단 `recommend_folder`는 `context.document_id`로 문서 snapshot을 조회하지 않는다. |
| 내 문서 구조를 보고 새 폴더가 필요한지 알려줘. | 현재 Task schema로는 핵심 입력을 표현할 수 없어 전용 schema/use case가 먼저 필요하다. | 부적절 | 현재 workflow step으로 핵심 입력이나 출력 계약을 안정적으로 만들 수 없다. |
| 관련 문서를 추천해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> recommend_documents`; anchor나 제외 대상이 필요하면 현재 schema로는 조건부다. |
### 구조화 능력 테스트

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 내 문서들을 주제별로 다시 분류해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=concept/entity) -> synthesize_signals`. |
| 이 문서를 문제, 원인, 해결책으로 나눠줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 이 폴더 내용을 하나의 목차 구조로 정리해줘. | `request`는 원문 그대로, `context.folder_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_folder`, `find_documents -> generate_draft`; `context.folder_id` 누락 시 `request_clarification`. |
### 실행 계획 능력 테스트

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 이 문서를 바탕으로 다음 액션 아이템을 뽑아줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 프로젝트를 진행하려면 단계별로 뭘 해야 하는지 알려줘. | 프로젝트가 폴더라면 `context.folder_id`를 붙여 현재 폴더 요청으로 바꾸고, 아니면 프로젝트명을 request에 명시한다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 이번 주에 해야 할 일만 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=commitment) -> synthesize_signals`가 의도된 경로지만 signal vector scope는 created_at/updated_at 필터를 지원하지 않아 날짜 조건은 조건부다. |
## 25. 가장 일반 사용자다운 요청 TOP 30

| 원문 요청 | Task로 보낼 요청/컨텍스트 | 판단 | 현재 처리 또는 한계 |
|---|---|---|---|
| 내 문서 좀 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 이 문서 요약해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 이거 어디 폴더에 넣어야 해? | `request`는 원문 그대로 보낼 수 있으나, 현재 문서 본문 snapshot을 Task가 받지 못해 추천 품질은 제한된다. | 조건부 적절 | `find_folders -> recommend_folder`; 단 `recommend_folder`는 `context.document_id`로 문서 snapshot을 조회하지 않는다. |
| 비슷한 문서 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 전에 이런 내용 쓴 적 있어? | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 최근에 쓴 문서 보여줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 중요한 문서만 골라줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 내가 해야 할 일 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=commitment) -> expand_signal_evidence(필요 시) -> synthesize_signals`. |
| 이 문서 제목 추천해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 폴더 안 내용 요약해줘. | `request`는 원문 그대로, `context.folder_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_folder`, `find_documents -> summarize_documents/answer_question`; `context.folder_id` 누락 시 `request_clarification`. |
| 중복된 문서 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 이 문서에서 중요한 부분만 알려줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 이 내용을 보기 좋게 정리해줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 내 메모를 주제별로 묶어줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=concept/entity) -> synthesize_signals`. |
| 이 프로젝트 관련 문서 모아줘. | 프로젝트가 폴더라면 `context.folder_id`를 붙여 현재 폴더 요청으로 바꾸고, 아니면 프로젝트명을 request에 명시한다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 내가 요즘 뭘 많이 적었는지 알려줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 오래된 문서 정리해줘. | 문서 상태/메타데이터 목록 필터를 받는 전용 list/review use case가 먼저 필요하다. | 부적절 | Task request에는 metadata/list filter와 상태 기반 batch 대상 지정이 없다. |
| 폴더 구조 추천해줘. | 현재 Task schema로는 핵심 입력을 표현할 수 없어 전용 schema/use case가 먼저 필요하다. | 부적절 | 현재 workflow step으로 핵심 입력이나 출력 계약을 안정적으로 만들 수 없다. |
| 이 문서에서 할 일 뽑아줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 회의록 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
| 이 아이디어 발전시켜줘. | 선택 텍스트/본문을 직접 보낼 수 없으므로 현재는 원문을 문서로 저장한 뒤 `context.document_id`를 붙여 보낸다. | 조건부 적절 | `find_documents -> explore_ideas/answer_question`; 선택 본문이 없으면 검색 evidence에 의존한다. |
| 문서들 합쳐서 최종본 만들어줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> generate_draft`; 새 문서 생성까지 요구하면 `plan_host_actions(create_document)`가 추가된다. |
| 이 문서가 괜찮은지 봐줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_documents -> answer_question`; `context.document_id` 누락 시 `request_clarification`. |
| 내 기록을 보고 이번 주 계획 세워줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> answer_question`; 요청 대상이 모호하면 retrieval 후보에 의존한다. |
| 내 문서에서 중요한 키워드 뽑아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_signals(signal_type=concept/entity) -> synthesize_signals`. |
| 관련 자료 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 이 문서 쉽게 설명해줘. | `request`는 원문 그대로, `context.document_id`를 반드시 함께 보낸다. | 적절 | `source_scope=current_document`, `find_signals(signal_type=summary) -> synthesize_signals`; `context.document_id` 누락 시 `request_clarification`. |
| 내 문서들에서 빠진 내용 찾아줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> present_documents`; 날짜 힌트는 `params.temporal`로 `created_at`/`updated_at` scope가 된다. |
| 나중에 다시 봐야 할 문서 추천해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> recommend_documents`; anchor나 제외 대상이 필요하면 현재 schema로는 조건부다. |
| 내 생각을 정리해줘. | `request`는 원문 그대로 보내고, `tenant`와 `context.requested_at`을 함께 둔다. | 조건부 적절 | `find_documents -> summarize_documents/answer_question`; 전체 corpus 보장은 없고 retrieval 후보 중심이다. |
