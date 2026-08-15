import uuid

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.agents.state import AgentState
from src.agents.nodes import (
    health_check_node,
    retrieve_context_node,
    diagnose_node,
    work_order_node,
    respond_node,
)


def should_create_work_order(state: AgentState) -> str:
    """Conditional edge: create work order only for HIGH or CRITICAL severity."""
    severity = (state.get("severity") or "").upper()
    if severity in ("HIGH", "CRITICAL"):
        return "create_work_order"
    return "respond"


def build_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("health_check", health_check_node)
    workflow.add_node("retrieve_context", retrieve_context_node)
    workflow.add_node("diagnose", diagnose_node)
    workflow.add_node("work_order", work_order_node)
    workflow.add_node("respond", respond_node)

    workflow.add_edge(START, "health_check")
    workflow.add_edge("health_check", "retrieve_context")
    workflow.add_edge("retrieve_context", "diagnose")
    workflow.add_conditional_edges(
        "diagnose",
        should_create_work_order,
        {"create_work_order": "work_order", "respond": "respond"},
    )
    workflow.add_edge("work_order", "respond")
    workflow.add_edge("respond", END)

    return workflow


checkpointer = MemorySaver()
graph = build_graph().compile(checkpointer=checkpointer)


def run_diagnostic(
    equipment_id: str,
    query: str,
    user_id: int = 1,
    thread_id: str = None,
) -> dict:
    """Run the full diagnostic workflow and return the final state."""
    thread_id = thread_id or str(uuid.uuid4())

    initial_state = AgentState(
        equipment_id=equipment_id,
        user_query=query,
        health_status=None,
        retrieved_docs=None,
        maintenance_history=None,
        diagnosis=None,
        root_cause=None,
        recommended_action=None,
        confidence_score=None,
        severity=None,
        work_order_created=False,
        work_order_id=None,
        work_order_data=None,
        error=None,
        messages=[],
        agent_steps=[],
    )

    config = {"configurable": {"thread_id": thread_id}}
    final_state = graph.invoke(initial_state, config=config)
    return dict(final_state)
