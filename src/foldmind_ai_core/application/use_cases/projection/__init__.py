"""Projection use case implementations."""

from .handle_document_chunk_vector_projection import (
    HandleDocumentChunkVectorDeletedProjectionUseCase,
    HandleDocumentChunkVectorIndexedProjectionUseCase,
)
from .handle_document_vector_projection import (
    HandleDocumentVectorDeletedProjectionUseCase,
    HandleDocumentVectorIndexedProjectionUseCase,
)
from .handle_folder_vector_projection import (
    HandleFolderVectorDeletedProjectionUseCase,
    HandleFolderVectorIndexedProjectionUseCase,
)
from .handle_graph_projection import (
    HandleDocumentGraphDeletedProjectionUseCase,
    HandleDocumentGraphIndexedProjectionUseCase,
    HandleFolderGraphDeletedProjectionUseCase,
    HandleFolderGraphIndexedProjectionUseCase,
)

__all__ = (
    "HandleDocumentChunkVectorDeletedProjectionUseCase",
    "HandleDocumentChunkVectorIndexedProjectionUseCase",
    "HandleDocumentGraphDeletedProjectionUseCase",
    "HandleDocumentGraphIndexedProjectionUseCase",
    "HandleDocumentVectorDeletedProjectionUseCase",
    "HandleDocumentVectorIndexedProjectionUseCase",
    "HandleFolderGraphDeletedProjectionUseCase",
    "HandleFolderGraphIndexedProjectionUseCase",
    "HandleFolderVectorDeletedProjectionUseCase",
    "HandleFolderVectorIndexedProjectionUseCase",
)
