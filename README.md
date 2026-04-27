# FoldMind-AI-Core

FoldMind-AI-Core is the AI workflow server behind FoldMind. It does not own source
documents or folders. The FoldMind app server remains the source of truth and calls
AI-Core over REST for indexing, retrieval, recommendations, generation, and workflow
step decisions.

## Responsibility Boundary

- FoldMind app server owns source documents, folders, permissions, and business rules.
- AI-Core owns AI indexes, retrieval results, generated artifacts, workflow state, and
  proposed host actions.
- AI-Core does not call the app server directly. It returns the next host action, and
  the app server executes that action and reports the result back.

## Current Package Layout

```text
src/ai_core/
  api/
    routes/        FastAPI route factories for app-server calls.
    dto/           REST request and response DTOs.
  domain/          Core business concepts and workflow contracts.
  application/
    use_cases/     App-server callable AI-Core operations.
    ports/         Provider, vector store, and task store protocols.
  workflows/       Planner, graph, executor, and workflow state.
  agents/          Specialized AI step implementations.
  infrastructure/  Concrete adapters for providers and persistence.
  schemas/         Backward-compatible contract re-exports.
  interfaces/      Backward-compatible port re-exports.
  common/          Shared primitive types.
```

The domain and application layers contain the stable core. `schemas` and
`interfaces` are compatibility layers for existing imports; new code should prefer
`ai_core.domain` and `ai_core.application.ports`.

## Core Concepts

- `SourceDocument` and `SourceFolder` are input snapshots supplied by the app server.
- `DocumentChunk` is the document indexing unit.
- `IndexedFolder` is the folder representative indexing unit.
- `HostAction` is an instruction for the app server to execute, such as
  `create_document`, `move_document`, or `link_documents`.
- `TaskSnapshot` represents a workflow-facing view of the current request state.

## Development

```bash
PYTHONPATH=src python -S -c "import ai_core.schemas; import ai_core.interfaces"
python -m compileall src
```
