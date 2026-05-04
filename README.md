# FoldMind-AI-Core

FoldMind-AI-Core is the AI workflow server behind FoldMind. It does not own source
documents or folders. The FoldMind app server remains the source of truth and calls
AI-Core over REST for indexing, retrieval, recommendations, generation, and workflow
step decisions.

## Responsibility Boundary

- FoldMind app server owns source documents, folders, permissions, and business rules.
- AI-Core owns AI indexes, retrieval results, generated outputs, workflow state, and
  proposed host actions.
- AI-Core does not call the app server directly. It returns the next host action, and
  the app server executes that action and reports the result back.

## Current Package Layout

```text
src/ai_core/
  bootstrap.py     Composition root helpers for wiring ports to use cases.
  api/
    app.py         FastAPI application factory and router composition.
    settings.py    API server settings.
    routes/        FastAPI route factories for app-server calls.
    dto/           REST request and response DTOs.
      action_inputs.py    Host action input payload DTOs.
      action_outputs.py   Host action result output DTOs.
      action_plans.py     Host action and action plan response DTOs.
      action_results.py   Host action result request DTOs.
      actions.py          Backward-compatible action DTO re-exports.
      documents.py        Document and folder snapshot DTOs.
      generation.py       Generated text, draft, and clarification DTOs.
      indexing.py         Index maintenance request and response DTOs.
      outputs.py          Typed task output DTOs.
      queries.py          Natural-language query context DTOs.
      recommendations.py  Recommendation request and response DTOs.
      retrieval.py        Search and QA retrieval DTOs.
      tasks.py            Task request, event, and snapshot DTOs.
  domain/          Core knowledge concepts.
  application/
    models/        Host action contracts and AI result models.
    use_cases/     App-server callable AI-Core operations.
    ports/         Provider, vector store, and task store protocols.
  workflows/       Planner, graph, executor, and workflow state.
    models/        Assistant execution and task state models.
  agents/          Specialized AI step implementations.
  infrastructure/  Concrete adapters for providers and persistence.
  common/          Shared primitive types.
```

The domain and application layers contain the stable core. External provider
and persistence contracts live in `ai_core.application.ports`.

API DTOs inherit from `APIBaseDTO`, a Pydantic base model that rejects unknown
fields at the REST boundary. Request DTOs provide `to_model()` methods, and response
DTOs provide `from_model()` constructors. This keeps REST serialization concerns at
the API edge while the application layer works with internal models.

`ai_core.api.app.create_app()` creates the FastAPI server from a complete
`APIUseCases` bundle and registers the API routers. `ai_core.bootstrap.build_use_cases()`
wires provider and persistence ports into application use cases, while concrete
adapter construction remains outside the route modules.

The domain layer only contains core knowledge concepts:

- `documents.py`: source and indexed document snapshots.
- `folders.py`: source and indexed folder snapshots.
- `chunks.py`: document chunk indexing units.

Application and workflow contracts are separated from domain:

- `application/models/actions.py`: host actions returned to the app server.
- `application/models/llm.py`: LLM provider message contracts.
- `application/models/queries.py`: natural-language request context and search scope.
- `application/models/retrieval.py`: retrieval result read models.
- `application/models/results.py`: assistant responses, generated text, drafts, and recommendations.
- `application/models/tasks.py`: app-server visible task snapshots, decisions, and events.
- `workflows/models/assistant.py`: assistant plans, run results, artifacts, and execution traces.

Task analysis results are represented as typed outputs instead of a growing set
of optional fields. This keeps task snapshots stable as new workflow result types
are added.

## Core Concepts

- `SourceDocument` and `SourceFolder` are input snapshots supplied by the app server.
- `DocumentChunk` is the document indexing unit.
- `IndexedFolder` is the folder representative indexing unit.
- `HostAction` is an instruction for the app server to execute, such as
  `create_document`, `move_document`, or `link_documents`.
- `TaskSnapshot` represents the app-server visible state of an AI workflow request.
- Hybrid search is modeled as dense vector retrieval plus keyword/sparse retrieval,
  fused with reciprocal rank fusion (RRF).

## Search

Document retrieval supports three modes through `HybridSearchConfig`:

- `dense`: embedding vector similarity only.
- `keyword`: keyword/sparse retrieval only.
- `hybrid`: dense and keyword results combined with RRF.

`DocumentVectorStore` owns dense retrieval. `DocumentKeywordSearchStore` owns
keyword/sparse retrieval. `HybridSearchConfig` and `SearchMode` live with
`HybridSearchUseCase` in the application layer because they are retrieval execution
options, not domain concepts. `HybridSearchUseCase` combines both result lists using
RRF.

## Development

```bash
python -m pip install -r requirements.txt
PYTHONPATH=src python -S -c "import ai_core.domain; import ai_core.application.ports"
PYTHONPATH=src python -m unittest discover -s tests
python -m compileall src
```
