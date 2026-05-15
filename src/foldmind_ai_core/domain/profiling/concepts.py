from __future__ import annotations

import re
import unicodedata
import uuid
from collections.abc import Iterable, Mapping
from typing import Any

from foldmind_ai_core.domain.common import Confidence
from foldmind_ai_core.domain.profiling.models import ProfileConcept

_CONCEPT_NAMESPACE = uuid.UUID("26a8f47a-947a-5bb8-9f4d-507d646d0169")
_SEPARATOR_PATTERN = re.compile(r"[^\w]+", re.UNICODE)


def concept_key(label: str) -> str:
    normalized = unicodedata.normalize("NFKC", label).casefold().strip()
    normalized = _SEPARATOR_PATTERN.sub("_", normalized)
    return normalized.strip("_")


def concept_id(*, tenant: str, key: str) -> str:
    return str(uuid.uuid5(_CONCEPT_NAMESPACE, f"concept:{tenant}:{key}"))


def concept_payloads(
    *,
    tenant: str,
    labels: Iterable[str],
    confidence: Confidence | float | None = None,
    evidence_chunk_ids: Mapping[str, Iterable[str]] | None = None,
) -> list[dict[str, Any]]:
    score = _confidence_value(confidence)
    evidence = evidence_chunk_ids or {}
    payloads: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_label in labels:
        label = str(raw_label).strip()
        key = concept_key(label)
        if not label or not key or key in seen:
            continue
        seen.add(key)
        payloads.append(
            {
                "concept_id": concept_id(tenant=tenant, key=key),
                "concept_key": key,
                "label": label,
                "confidence": score,
                "evidence_chunk_ids": [
                    str(chunk_id) for chunk_id in evidence.get(label, ())
                ],
            }
        )
    return payloads


def profile_concepts_from_labels(
    *,
    tenant: str,
    labels: Iterable[str],
    confidence: Confidence | float | None = None,
    evidence_chunk_ids: Mapping[str, Iterable[str]] | None = None,
) -> tuple[ProfileConcept, ...]:
    return tuple(
        ProfileConcept(
            concept_id=str(payload["concept_id"]),
            concept_key=str(payload["concept_key"]),
            label=str(payload["label"]),
            confidence=_confidence_value(confidence),
            evidence_chunk_ids=tuple(
                str(chunk_id) for chunk_id in payload.get("evidence_chunk_ids", ())
            ),
        )
        for payload in concept_payloads(
            tenant=tenant,
            labels=labels,
            confidence=confidence,
            evidence_chunk_ids=evidence_chunk_ids,
        )
    )


def _confidence_value(confidence: Confidence | float | None) -> float | None:
    if isinstance(confidence, Confidence):
        return confidence.value
    if confidence is None:
        return None
    return float(confidence)
