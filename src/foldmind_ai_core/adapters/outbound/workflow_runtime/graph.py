from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass, field
from typing import Any, TypeAlias, cast

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from foldmind_ai_core.adapters.outbound.workflow_runtime import routes
from foldmind_ai_core.adapters.outbound.workflow_runtime.checkpoint_codec import (
    checkpoint_value,
    workflow_state_from_checkpoint,
    workflow_state_to_checkpoint,
)
from foldmind_ai_core.adapters.outbound.workflow_runtime.graph_state import GraphState
from foldmind_ai_core.adapters.outbound.workflow_runtime.nodes import LangGraphWorkflowNodes
from foldmind_ai_core.core.application.workflows.engine import WorkflowEngine
from foldmind_ai_core.core.application.workflows.state.plan import WorkflowActionType
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.domain.models.workflow.actions import HostActionResult
from foldmind_ai_core.core.domain.models.workflow.tasks import TaskSnapshot

GraphBuilder: TypeAlias = StateGraph[GraphState, None, GraphState, GraphState]


@dataclass(slots=True)
class LangGraphWorkflowGraph:
    engine: WorkflowEngine
    checkpointer: Any
    _nodes: LangGraphWorkflowNodes = field(init=False, repr=False)
    _graph: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.checkpointer is None:
            raise RuntimeError("LangGraphWorkflowGraph requires a durable checkpointer.")
        self._nodes = LangGraphWorkflowNodes(self.engine)
        self._graph = self.__compile()

    def run(self, snapshot: TaskSnapshot) -> TaskSnapshot:
        thread_config = {"configurable": {"thread_id": snapshot.task_id}}
        result = self._graph.invoke(
            workflow_state_to_checkpoint(WorkflowState(task=snapshot)),
            thread_config,
        )
        return workflow_state_from_checkpoint(result).task

    def resume_from_action_result(
        self,
        *,
        task_id: str,
        result: HostActionResult,
    ) -> TaskSnapshot:
        graph_state = self._graph.invoke(
            Command(resume=checkpoint_value(result)),
            {"configurable": {"thread_id": task_id}},
        )
        return workflow_state_from_checkpoint(graph_state).task

    def __compile(self) -> Any:
        builder: GraphBuilder = StateGraph(GraphState)
        self.__add_nodes(builder)
        self.__add_edges(builder)
        return builder.compile(checkpointer=self.checkpointer)

    def __add_nodes(self, builder: GraphBuilder) -> None:
        builder.add_node(routes.PLAN, self._nodes.plan)
        builder.add_node(routes.ROUTE_STEP, self._nodes.route_step_node)
        for action_type in WorkflowActionType:
            builder.add_node(
                str(action_type),
                cast(Any, self._nodes.step(action_type)),
                input_schema=GraphState,
            )
        builder.add_node(routes.REPLAN, self._nodes.replan)
        builder.add_node(routes.RETRY_STEP, self._nodes.retry_step)
        builder.add_node(routes.RETRY_HOST_ACTION, self._nodes.retry_host_action)
        builder.add_node(routes.FAIL, self._nodes.fail)
        builder.add_node(routes.WAIT_FOR_HOST_ACTION, self._nodes.wait_for_host_action)
        builder.add_node(
            routes.RESUME_FROM_ACTION_RESULT,
            self._nodes.resume_from_action_result,
        )

    def __add_edges(self, builder: GraphBuilder) -> None:
        builder.add_edge(START, routes.PLAN)
        builder.add_edge(routes.PLAN, routes.ROUTE_STEP)
        builder.add_edge(routes.REPLAN, routes.ROUTE_STEP)
        builder.add_edge(routes.RETRY_HOST_ACTION, routes.WAIT_FOR_HOST_ACTION)
        builder.add_edge(routes.FAIL, END)
        builder.add_conditional_edges(
            routes.ROUTE_STEP,
            self._nodes.route_step,
            self.__path_map(routes.STEP_ROUTES),
        )
        for node_name in routes.STEP_NODE_NAMES:
            builder.add_conditional_edges(
                node_name,
                self._nodes.route_after_step,
                self.__path_map(routes.AFTER_STEP_ROUTES),
            )
        builder.add_conditional_edges(
            routes.RETRY_STEP,
            self._nodes.route_after_step,
            self.__path_map(routes.AFTER_STEP_ROUTES),
        )
        builder.add_edge(routes.WAIT_FOR_HOST_ACTION, routes.RESUME_FROM_ACTION_RESULT)
        builder.add_conditional_edges(
            routes.RESUME_FROM_ACTION_RESULT,
            self._nodes.route_after_resume,
            self.__path_map(routes.AFTER_RESUME_ROUTES),
        )

    @staticmethod
    def __path_map(path_map: dict[str, str]) -> dict[Hashable, str]:
        return cast(dict[Hashable, str], path_map)
