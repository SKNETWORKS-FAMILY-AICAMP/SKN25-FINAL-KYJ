from __future__ import annotations

from dataclasses import dataclass

from ai_core.application.models.results import FolderRecommendation, FolderRecommendationResult
from ai_core.application.ports.embedding import EmbeddingProvider
from ai_core.application.ports.folder_vector_store import FolderVectorStore
from ai_core.domain.documents import SourceDocument


@dataclass(slots=True)
class FolderRecommenderAgent:
    embeddings: EmbeddingProvider
    folders: FolderVectorStore
    top_k: int = 5

    def recommend(self, document: SourceDocument) -> FolderRecommendationResult:
        vector = self.embeddings.embed_texts([document.full_text])[0]
        matches = self.folders.similarity_search(
            tenant=document.tenant,
            query_vector=vector,
            top_k=self.top_k,
        )
        if not matches:
            raise ValueError("No folder candidates found.")

        recommendations = [
            FolderRecommendation(
                folder=match.folder,
                reason="Folder vector is semantically close to the document.",
                score=match.score,
            )
            for match in matches
        ]
        return FolderRecommendationResult(
            primary=recommendations[0],
            alternatives=recommendations[1:],
        )
