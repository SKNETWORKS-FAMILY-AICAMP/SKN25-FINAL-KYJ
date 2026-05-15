from __future__ import annotations
from dataclasses import dataclass

from foldmind_ai_core.application.workflows.host_actions.build_context import HostActionBuildContext
from foldmind_ai_core.domain.generation.results import (
    DocumentRecommendation,
    DraftResult,
    FolderRecommendationResult,
    GeneratedTextResult,
    RelatedRecommendationResult,
)
from foldmind_ai_core.domain.workflow.actions import (
    ActionPlan,
    CreateDocumentInput,
    CreateFolderInput,
    HostAction,
    HostActionInput,
    HostActionPolicy,
    HostActionStatus,
    HostActionType,
    LinkDocumentsInput,
    MoveDocumentInput,
    UpdateDocumentInput,
)
from foldmind_ai_core.domain.workflow.tasks import TaskSnapshot
from foldmind_ai_core.shared.internal_ids import stable_internal_id
from foldmind_ai_core.shared.types import Metadata


@dataclass(slots=True)
class HostActionBuilder:
    def build(
        self,
        *,
        task: TaskSnapshot,
        round_index: int = 0,
        draft: DraftResult | None = None,
        summary: GeneratedTextResult | None = None,
        synthesized_report: GeneratedTextResult | None = None,
        folder_recommendation: FolderRecommendationResult | None = None,
        related_recommendation: RelatedRecommendationResult | None = None,
        requested_actions: tuple[HostActionType, ...] = (),
        options: Metadata | None = None,
    ) -> ActionPlan:
        options = options or {}
        document_body = self._document_body(
            draft=draft,
            summary=summary,
            synthesized_report=synthesized_report,
            options=options,
        )
        requested = set(requested_actions)
        create_folder_action_id = self._requested_action_id(
            task,
            HostActionType.CREATE_FOLDER,
            round_index,
            requested,
        )
        create_document_action_id = None
        if document_body is not None:
            create_document_action_id = self._requested_action_id(
                task,
                HostActionType.CREATE_DOCUMENT,
                round_index,
                requested,
            )

        ctx = HostActionBuildContext(
            task=task,
            round_index=round_index,
            folder_recommendation=folder_recommendation,
            related_recommendation=related_recommendation,
            options=options,
            policy=self._policy(options),
            document_body=document_body,
            create_folder_action_id=create_folder_action_id,
            create_document_action_id=create_document_action_id,
        )
        actions: list[HostAction] = []

        if HostActionType.CREATE_FOLDER in requested:
            actions.append(self._create_folder(ctx))
        if HostActionType.CREATE_DOCUMENT in requested:
            action = self._create_document(ctx)
            if action is not None:
                actions.append(action)
        if HostActionType.MOVE_DOCUMENT in requested:
            action = self._move_document(ctx)
            if action is not None:
                actions.append(action)
        if HostActionType.UPDATE_DOCUMENT in requested:
            action = self._update_document(ctx)
            if action is not None:
                actions.append(action)
        if HostActionType.LINK_DOCUMENTS in requested:
            action = self._link_documents(ctx)
            if action is not None:
                actions.append(action)

        return ActionPlan(
            summary="Host action plan.",
            steps=[action.summary for action in actions] or ["No host actions proposed."],
            host_actions=actions,
        )

    def _create_folder(self, ctx: HostActionBuildContext) -> HostAction:
        folder_name = self._folder_name(ctx.task.request, ctx.options)
        return self._action(
            ctx,
            HostActionType.CREATE_FOLDER,
            summary=f"Create folder '{folder_name}'.",
            reason="The workflow needs a destination folder before writing documents.",
            input=CreateFolderInput(
                name=folder_name,
                parent_folder_id=self._optional_str(ctx.options.get("parent_folder_id")),
                metadata=self._source_metadata(ctx.task),
            ),
        )

    def _create_document(self, ctx: HostActionBuildContext) -> HostAction | None:
        if ctx.document_body is None:
            return None
        metadata = self._source_metadata(ctx.task)
        depends_on = self._depends_on(ctx.create_folder_action_id)
        if ctx.create_folder_action_id is not None:
            metadata["folder_action_id"] = ctx.create_folder_action_id
        return self._action(
            ctx,
            HostActionType.CREATE_DOCUMENT,
            summary="Create a document from the generated draft.",
            reason="The user asked to turn the retrieved information into a document.",
            input=CreateDocumentInput(
                title=self._title_for_document(ctx.task.request, ctx.options),
                body=ctx.document_body,
                folder_id=self._folder_id(ctx.folder_recommendation),
                metadata=metadata,
            ),
            depends_on=depends_on,
        )

    def _move_document(self, ctx: HostActionBuildContext) -> HostAction | None:
        if ctx.folder_recommendation is None:
            return None
        source = self._source(ctx.task, ctx.options)
        if source is None:
            return None
        source_type, source_id = source
        return self._action(
            ctx,
            HostActionType.MOVE_DOCUMENT,
            summary="Move the document to the recommended folder.",
            reason="The recommended folder is the best semantic match for this document.",
            input=MoveDocumentInput(
                document_type=source_type,
                document_id=source_id,
                target_folder_id=ctx.folder_recommendation.primary.folder_id,
                source_folder_id=self._optional_str(ctx.options.get("source_folder_id")),
            ),
        )

    def _update_document(self, ctx: HostActionBuildContext) -> HostAction | None:
        if not self._has_update_payload(body=ctx.document_body, options=ctx.options):
            return None
        source = self._source(ctx.task, ctx.options)
        if source is None:
            return None
        source_type, source_id = source
        return self._action(
            ctx,
            HostActionType.UPDATE_DOCUMENT,
            summary="Update the source document.",
            reason="The user asked to update an existing document.",
            input=UpdateDocumentInput(
                document_type=source_type,
                document_id=source_id,
                title=self._optional_str(ctx.options.get("title")),
                body=ctx.document_body,
                tag_ids=self._string_tuple(ctx.options.get("tag_ids")),
                metadata=self._metadata_update(ctx.options),
            ),
            metadata={"source_task_id": ctx.task.task_id},
        )

    def _link_documents(self, ctx: HostActionBuildContext) -> HostAction | None:
        link_input = self._link_input(
            ctx.task,
            ctx.options,
            ctx.related_recommendation,
            source_action_id=ctx.create_document_action_id,
        )
        if link_input is None:
            return None
        return self._action(
            ctx,
            HostActionType.LINK_DOCUMENTS,
            summary="Link related documents.",
            reason="The workflow found related knowledge assets.",
            input=link_input,
            depends_on=self._depends_on(ctx.create_document_action_id),
        )

    def _action(
        self,
        ctx: HostActionBuildContext,
        action_type: HostActionType,
        *,
        summary: str,
        reason: str,
        input: HostActionInput,
        depends_on: list[str] | None = None,
        metadata: Metadata | None = None,
    ) -> HostAction:
        depends_on = depends_on or []
        return HostAction(
            action_type=action_type,
            action_id=self._action_id(ctx.task, action_type.value, ctx.round_index),
            summary=summary,
            reason=reason,
            status=self._initial_status(depends_on),
            input=input,
            depends_on=depends_on,
            metadata=metadata or {},
            policy=ctx.policy,
        )

    def _depends_on(self, action_id: str | None) -> list[str]:
        return [action_id] if action_id is not None else []

    def _source_metadata(self, task: TaskSnapshot) -> Metadata:
        return {"source_task_id": task.task_id, "source_request": task.request}

    def _initial_status(self, depends_on: list[str]) -> HostActionStatus:
        return HostActionStatus.PROPOSED if depends_on else HostActionStatus.READY

    def _policy(self, options: Metadata) -> HostActionPolicy:
        requires_confirmation = options.get("requires_confirmation", True)
        return HostActionPolicy(
            max_attempts=self._positive_int(options.get("max_attempts"), default=2),
            retryable=bool(options.get("retryable", True)),
            requires_confirmation=bool(requires_confirmation),
        )

    def _positive_int(self, value: object, *, default: int) -> int:
        if isinstance(value, int) and value > 0:
            return value
        return default

    def _folder_name(self, request: str, options: Metadata) -> str:
        folder_name = options.get("folder_name")
        if isinstance(folder_name, str) and folder_name.strip():
            return folder_name.strip()
        topic = options.get("topic")
        if isinstance(topic, str) and topic.strip():
            return topic.strip()
        return self._title_for_document(request, options)

    def _document_body(
        self,
        *,
        draft: DraftResult | None,
        summary: GeneratedTextResult | None,
        synthesized_report: GeneratedTextResult | None,
        options: Metadata,
    ) -> str | None:
        body = options.get("body")
        if isinstance(body, str) and body.strip():
            return body.strip()
        if draft is not None:
            return draft.draft
        if synthesized_report is not None:
            return synthesized_report.text
        if summary is not None:
            return summary.text
        return None

    def _title_for_document(self, request: str, options: Metadata) -> str:
        title = options.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()

        normalized = " ".join(request.split())
        for marker in ("에 관련된", "에 관한", "관련", "about"):
            if marker in normalized:
                subject = normalized.split(marker, maxsplit=1)[0].strip()
                if subject:
                    return f"{subject} 관련 문서 정리"
        if len(normalized) <= 60:
            return normalized
        return f"{normalized[:57].rstrip()}..."

    def _folder_id(self, recommendation: FolderRecommendationResult | None) -> str | None:
        if recommendation is None:
            return None
        return recommendation.primary.folder_id

    def _source(self, task: TaskSnapshot, options: Metadata) -> tuple[str, str] | None:
        document_data = self._document_metadata(task)
        document_id = self._first_non_blank(
            options.get("document_id"),
            document_data.get("document_id"),
        )
        if document_id is None:
            return None
        document_type = self._first_non_blank(
            options.get("document_type"),
            document_data.get("document_type"),
        ) or "document"
        return document_type, document_id

    def _document_metadata(self, task: TaskSnapshot) -> Metadata:
        document_data = task.metadata.get("document", {})
        if not isinstance(document_data, dict):
            return {}
        return document_data

    def _optional_str(self, value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _first_non_blank(self, *values: object) -> str | None:
        for value in values:
            text = self._optional_str(value)
            if text is not None:
                return text
        return None

    def _string_tuple(self, value: object) -> tuple[str, ...] | None:
        if value is None:
            return None
        if isinstance(value, str):
            return (value,) if value.strip() else None
        if isinstance(value, list | tuple):
            values = tuple(str(item) for item in value if str(item).strip())
            return values or None
        return None

    def _metadata_update(self, options: Metadata) -> Metadata:
        value = options.get("metadata")
        return dict(value) if isinstance(value, dict) else {}

    def _has_update_payload(self, *, body: str | None, options: Metadata) -> bool:
        has_title = self._optional_str(options.get("title")) is not None
        has_tags = self._string_tuple(options.get("tag_ids")) is not None
        has_metadata = bool(self._metadata_update(options))
        return body is not None or has_title or has_tags or has_metadata

    def _link_input(
        self,
        task: TaskSnapshot,
        options: Metadata,
        related_recommendation: RelatedRecommendationResult | None,
        *,
        source_action_id: str | None = None,
    ) -> LinkDocumentsInput | None:
        metadata: Metadata = {"source_task_id": task.task_id}
        source = self._link_source(task, options, source_action_id)
        if source is None:
            return None
        source_type, source_id = source
        target = self._link_target(options, related_recommendation)
        if target is None:
            return None
        target_type, target_id = target
        relationship = self._optional_str(options.get("relationship")) or "related"
        return LinkDocumentsInput(
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            relationship=relationship,
            metadata=metadata,
        )

    def _link_source(
        self,
        task: TaskSnapshot,
        options: Metadata,
        source_action_id: str | None,
    ) -> tuple[str, str] | None:
        source = self._source(task, options)
        if source is not None:
            return source
        if source_action_id is not None:
            return "document", source_action_id
        return None

    def _link_target(
        self,
        options: Metadata,
        related_recommendation: RelatedRecommendationResult | None,
    ) -> tuple[str, str] | None:
        explicit_target = self._explicit_link_target(options)
        if explicit_target is not None:
            return explicit_target
        return self._recommended_link_target(related_recommendation)

    def _explicit_link_target(self, options: Metadata) -> tuple[str, str] | None:
        target_type = self._optional_str(options.get("target_type"))
        target_id = self._optional_str(options.get("target_id"))
        if target_type is None or target_id is None:
            return None
        return target_type, target_id

    def _recommended_link_target(
        self,
        related_recommendation: RelatedRecommendationResult | None,
    ) -> tuple[str, str] | None:
        if related_recommendation is None or not related_recommendation.items:
            return None
        target = related_recommendation.items[0].target
        if not isinstance(target, DocumentRecommendation):
            return None
        return target.document.document_type, target.document.document_id

    def _requested_action_id(
        self,
        task: TaskSnapshot,
        action_type: HostActionType,
        round_index: int,
        requested: set[HostActionType],
    ) -> str | None:
        if action_type not in requested:
            return None
        return self._action_id(task, action_type.value, round_index)

    def _action_id(self, task: TaskSnapshot, name: str, round_index: int) -> str:
        return stable_internal_id("host-action", task.task_id, round_index, name)
