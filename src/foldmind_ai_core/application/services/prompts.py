from __future__ import annotations

import re

from foldmind_ai_core.shared.validation import InvalidInputError

PROMPT_ANSWER_GENERATION = "answer_generation"
PROMPT_DRAFT_GENERATION = "draft_generation"
PROMPT_IDEAS_EXPLORATION = "ideas_exploration"
PROMPT_DOCUMENT_PROFILING = "document_profiling"
PROMPT_CHUNK_RELEVANCE_VALIDATION = "chunk_relevance_validation"
PROMPT_SUMMARIZATION = "summarization"
PROMPT_WORKFLOW_PLANNING = "workflow_planning"

TOKEN_ALLOWED_WORKFLOW_ACTION_TYPES = "ALLOWED_WORKFLOW_ACTION_TYPES"
TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION = "UNTRUSTED_CONTEXT_INSTRUCTION"

_TOKEN_PATTERN = re.compile(r"\{\{([^{}]+)\}\}")
_SUPPORTED_TOKENS = {
    TOKEN_ALLOWED_WORKFLOW_ACTION_TYPES,
    TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION,
}


def render_prompt(template: str, tokens: dict[str, str] | None = None) -> str:
    tokens = tokens or {}
    unsupported = sorted(set(tokens) - _SUPPORTED_TOKENS)
    if unsupported:
        raise InvalidInputError(f"Unsupported prompt token(s): {', '.join(unsupported)}")

    rendered = template
    for name, value in tokens.items():
        rendered = rendered.replace(f"{{{{{name}}}}}", value)

    unresolved = sorted(set(_TOKEN_PATTERN.findall(rendered)))
    if unresolved:
        raise InvalidInputError(f"Unresolved prompt token(s): {', '.join(unresolved)}")
    return rendered.strip()
