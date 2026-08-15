from typing import Annotated, List, Optional, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    equipment_id: str
    user_query: str
    health_status: Optional[dict]
    retrieved_docs: Optional[List[str]]
    maintenance_history: Optional[List[str]]
    diagnosis: Optional[str]
    root_cause: Optional[str]
    recommended_action: Optional[str]
    confidence_score: Optional[float]
    severity: Optional[str]
    work_order_created: Optional[bool]
    work_order_id: Optional[str]
    work_order_data: Optional[dict]
    error: Optional[str]
    messages: Annotated[List[BaseMessage], add_messages]
    agent_steps: List[str]
