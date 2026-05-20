from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from foldmind_ai_core.core.application.workflows.host_actions.build_context import HostActionBuildContext
from foldmind_ai_core.core.application.workflows.option_values import (
    bool_option,
    metadata_option,
    optional_text_value,
    positive_int_option,
)
from foldmind_ai_core.core.domain.models.generation.results import (
    DocumentRecommendation,
    DraftResult,
    FolderRecommendationResult,
    GeneratedTextResult,
    RelatedRecommendationResult,
)
from foldmind_ai_core.core.domain.models.workflow.actions import (
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
from foldmind_ai_core.core.domain.models.workflow.tasks import TaskSnapshot
from foldmind_ai_core.shared.internal_ids import stable_internal_id
from foldmind_ai_core.shared.types import JsonObject, Metadata


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
        options: JsonObject | None = None,
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

        action_builders: tuple[
            tuple[
                HostActionType,
                Callable[[HostActionBuildContext], HostAction | None],
            ],
            ...,
        ] = (
            (HostActionType.CREATE_FOLDER, self._create_folder),
            (HostActionType.CREATE_DOCUMENT, self._create_document),
            (HostActionType.MOVE_DOCUMENT, self._move_document),
            (HostActionType.UPDATE_DOCUMENT, self._update_document),
            (HostActionType.LINK_DOCUMENTS, self._link_documents),
        )
        for action_type, build_action in action_builders:
            if action_type not in requested:
                continue
            action = build_action(ctx)
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
                parent_folder_id=optional_text_value(
                    ctx.options.get("parent_folder_id"),
                    name="parent_folder_id option",
                ),
                metadata=self._source_metadata(ctx.task),
            ),
        )

    def _create_document(self, ctx: HostActionBuildContext) -> HostAction | None:
        if ctx.document_body is None:
            return None
        metadata = self._source_metadata(ctx.task)
        folder_id = (
            ctx.folder_recommendation.primary.folder_id
            if ctx.folder_recommendation is not None
            else None
        )
        if ctx.create_folder_action_id is not None:
            metadata["folder_action_id"] = ctx.create_folder_action_id
            folder_id = None
        return self._action(
            ctx,
            HostActionType.CREATE_DOCUMENT,
            summary="Create a document from the generated draft.",
            reason="The user asked to turn the retrieved information into a document.",
            input=CreateDocumentInput(
                title=self._title_for_document(ctx.task.request, ctx.options),
                body=ctx.document_body,
                folder_id=folder_id,
                metadata=metadata,
            ),
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
                source_folder_id=optional_text_value(
                    ctx.options.get("source_folder_id"),
                    name="source_folder_id option",
                ),
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
                title=optional_text_value(ctx.options.get("title"), name="title option"),
                body=ctx.document_body,
                metadata=metadata_option(ctx.options),
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
        )

    def _action(
        self,
        ctx: HostActionBuildContext,
        action_type: HostActionType,
        *,
        summary: str,
        reason: str,
        input: HostActionInput,
        metadata: Metadata | None = None,
    ) -> HostAction:
        status = (
            HostActionStatus.PROPOSED
            if ctx.policy.requires_confirmation
            else HostActionStatus.READY
        )
        return HostAction(
            action_type=action_type,
            action_id=self._action_id(ctx.task, action_type.value, ctx.round_index),
            summary=summary,
            reason=reason,
            status=status,
            input=input,
            metadata=metadata or {},
            policy=ctx.policy,
        )

    def _source_metadata(self, task: TaskSnapshot) -> Metadata:
        return {"source_task_id": task.task_id, "source_request": task.request}

    def _policy(self, options: JsonObject) -> HostActionPolicy:
        return HostActionPolicy(
            max_attempts=positive_int_option(options, "max_attempts", default=2),
            allow_skip=bool_option(options, "allow_skip", default=False),
            retryable=bool_option(options, "retryable", default=True),
            requires_confirmation=bool_option(
                options,
                "requires_confirmation",
                default=True,
            ),
        )

    def _folder_name(self, request: str, options: JsonObject) -> str:
        folder_name = optional_text_value(options.get("folder_name"), name="folder_name option")
        if folder_name is not None:
            return folder_name
        topic = optional_text_value(options.get("topic"), name="topic option")
        if topic is not None:
            return topic
        return self._title_for_document(request, options)

    def _document_body(
        self,
        *,
        draft: DraftResult | None,
        summary: GeneratedTextResult | None,
        synthesized_report: GeneratedTextResult | None,
        options: JsonObject,
    ) -> str | None:
        body = optional_text_value(options.get("body"), name="body option")
        if body is not None:
            return body
        if draft is not None and draft.draft.strip():
            return draft.draft
        if synthesized_report is not None and synthesized_report.text.strip():
            return synthesized_report.text
        if summary is not None and summary.text.strip():
            return summary.text
        return None

    def _title_for_document(self, request: str, options: JsonObject) -> str:
        title = optional_text_value(options.get("title"), name="title option")
        if title is not None:
            return title

        normalized = " ".join(request.split())
        for marker in ("에 관련된", "에 관한", "관련", "about"):
            if marker in normalized:
                subject = normalized.split(marker, maxsplit=1)[0].strip()
                if subject:
                    return f"{subject} 관련 문서 정리"
        if len(normalized) <= 60:
            return normalized
        return f"{normalized[:57].rstrip()}..."

    def _source(self, task: TaskSnapshot, options: JsonObject) -> tuple[str, str] | None:
        document_data = task.metadata.get("document", {})
        if not isinstance(document_data, dict):
            document_data = {}
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

    def _first_non_blank(self, *values: object) -> str | None:
        for value in values:
            text = optional_text_value(value, name="document identity value")
            if text is not None:
                return text
        return None

    def _has_update_payload(self, *, body: str | None, options: JsonObject) -> bool:
        has_title = optional_text_value(options.get("title"), name="title option") is not None
        has_metadata = bool(metadata_option(options))
        return body is not None or has_title or has_metadata

    def _link_input(
        self,
        task: TaskSnapshot,
        options: JsonObject,
        related_recommendation: RelatedRecommendationResult | None,
        *,
        source_action_id: str | None = None,
    ) -> LinkDocumentsInput | None:
        metadata: Metadata = {"source_task_id": task.task_id}
        source = self._link_source(task, options, source_action_id)
        if source is None:
            return None
        source_type, source_id = source
        target = self._explicit_link_target(options) or self._recommended_link_target(
            related_recommendation
        )
        if target is None:
            return None
        target_type, target_id = target
        relationship = (
            optional_text_value(options.get("relationship"), name="relationship option")
            or "related"
        )
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
        options: JsonObject,
        source_action_id: str | None,
    ) -> tuple[str, str] | None:
        source = self._source(task, options)
        if source is not None:
            return source
        if source_action_id is not None:
            return "document", source_action_id
        return None

    def _explicit_link_target(self, options: JsonObject) -> tuple[str, str] | None:
        target_type = optional_text_value(options.get("target_type"), name="target_type option")
        target_id = optional_text_value(options.get("target_id"), name="target_id option")
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
