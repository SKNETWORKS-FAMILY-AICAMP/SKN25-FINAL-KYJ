from __future__ import annotations

from langgraph.graph import END

from foldmind_ai_core.core.application.workflows.state.plan import WorkflowActionType

PLAN = "plan"
ROUTE_STEP = "route_step"
REPLAN = "replan"
RETRY_STEP = "retry_step"
RETRY_HOST_ACTION = "retry_host_action"
FAIL = "fail"
WAIT_FOR_HOST_ACTION = "wait_for_host_action"
RESUME_FROM_ACTION_RESULT = "resume_from_action_result"
STEP_NODE_NAMES = tuple(str(action_type) for action_type in WorkflowActionType)
STEP_ROUTES = {node_name: node_name for node_name in STEP_NODE_NAMES} | {END: END}

AFTER_STEP_ROUTES = {
    ROUTE_STEP: ROUTE_STEP,
    WAIT_FOR_HOST_ACTION: WAIT_FOR_HOST_ACTION,
    RETRY_STEP: RETRY_STEP,
    FAIL: FAIL,
    END: END,
}

AFTER_RESUME_ROUTES = {
    ROUTE_STEP: ROUTE_STEP,
    WAIT_FOR_HOST_ACTION: WAIT_FOR_HOST_ACTION,
    REPLAN: REPLAN,
    RETRY_HOST_ACTION: RETRY_HOST_ACTION,
    FAIL: FAIL,
    END: END,
}
