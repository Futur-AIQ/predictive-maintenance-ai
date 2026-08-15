import json
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import HumanMessage, AIMessage
from loguru import logger

from src.agents.state import AgentState
from src.agents.tools import (
    get_equipment_health_status,
    retrieve_technical_documentation,
    retrieve_maintenance_history,
    create_work_order,
    calculate_maintenance_priority,
)
from src.config import settings


def _get_llm():
    """Try OpenRouter → Anthropic → OpenAI, return first available LLM."""
    # Try OpenRouter (OpenAI-compatible API)
    if settings.openrouter_api_key and settings.openrouter_model:
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
                model=settings.openrouter_model,
                temperature=0,
            )
            logger.info(f"Using OpenRouter LLM: {settings.openrouter_model}")
            return llm
        except Exception as e:
            logger.warning(f"OpenRouter unavailable: {e}")

    # Try Anthropic
    if settings.anthropic_api_key:
        try:
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(
                api_key=settings.anthropic_api_key,
                model="claude-sonnet-4-5",
                temperature=0,
            )
            logger.info("Using Anthropic Claude claude-sonnet-4-5")
            return llm
        except Exception as e:
            logger.warning(f"Anthropic unavailable: {e}")

    # Fallback to OpenAI
    if settings.openai_api_key:
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                api_key=settings.openai_api_key,
                model="gpt-4o-mini",
                temperature=0,
            )
            logger.info("Using OpenAI gpt-4o-mini fallback")
            return llm
        except Exception as e:
            logger.warning(f"OpenAI unavailable: {e}")

    raise RuntimeError(
        "No LLM available. Configure OPENROUTER_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY."
    )


def health_check_node(state: AgentState) -> dict:
    """Node 1: Check equipment health status."""
    equipment_id = state["equipment_id"]
    agent_steps = list(state.get("agent_steps") or [])

    logger.info(f"[health_check_node] Checking health for {equipment_id}")

    try:
        raw_result = get_equipment_health_status.invoke({"equipment_id": equipment_id})
        health_dict = json.loads(raw_result)
        status = health_dict.get("status", "UNKNOWN")
        health_score = health_dict.get("health_score", 0)
    except Exception as e:
        logger.error(f"[health_check_node] Failed to get health status: {e}")
        health_dict = {
            "equipment_id": equipment_id,
            "equipment_type": "unknown",
            "health_score": 50,
            "rul": 100,
            "status": "UNKNOWN",
            "sensor_readings": {},
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        status = "UNKNOWN"
        health_score = 50

    agent_steps.append(
        f"Health check completed: status={status}, health_score={health_score}"
    )

    return {
        "health_status": health_dict,
        "agent_steps": agent_steps,
    }


def retrieve_context_node(state: AgentState) -> dict:
    """Node 2: Retrieve technical documentation and maintenance history."""
    equipment_id = state["equipment_id"]
    user_query = state["user_query"]
    agent_steps = list(state.get("agent_steps") or [])

    # Derive equipment type from health_status if available
    health_status = state.get("health_status") or {}
    equipment_type = health_status.get("equipment_type", None)

    logger.info(
        f"[retrieve_context_node] Retrieving context for {equipment_id}, "
        f"equipment_type={equipment_type}"
    )

    # Retrieve technical documentation
    try:
        tech_docs_raw = retrieve_technical_documentation.invoke(
            {"query": user_query, "equipment_type": equipment_type}
        )
        # Split into individual document entries on the separator used in the tool
        tech_doc_entries = [
            chunk.strip()
            for chunk in tech_docs_raw.split("---")
            if chunk.strip()
        ]
    except Exception as e:
        logger.error(f"[retrieve_context_node] Failed to retrieve technical docs: {e}")
        tech_doc_entries = [f"Error retrieving technical documentation: {str(e)}"]

    # Retrieve maintenance history
    try:
        maint_history_raw = retrieve_maintenance_history.invoke(
            {"equipment_id": equipment_id}
        )
        maint_history_entries = [
            chunk.strip()
            for chunk in maint_history_raw.split("---")
            if chunk.strip()
        ]
    except Exception as e:
        logger.error(f"[retrieve_context_node] Failed to retrieve maintenance history: {e}")
        maint_history_entries = [f"Error retrieving maintenance history: {str(e)}"]

    n_docs = len(tech_doc_entries)
    n_logs = len(maint_history_entries)

    agent_steps.append(
        f"Context retrieved: {n_docs} technical docs, {n_logs} maintenance logs"
    )

    return {
        "retrieved_docs": tech_doc_entries,
        "maintenance_history": maint_history_entries,
        "agent_steps": agent_steps,
    }


def diagnose_node(state: AgentState) -> dict:
    """Node 3: Use LLM to diagnose the fault."""
    equipment_id = state["equipment_id"]
    user_query = state["user_query"]
    agent_steps = list(state.get("agent_steps") or [])

    health_status = state.get("health_status") or {}
    retrieved_docs = state.get("retrieved_docs") or []
    maintenance_history = state.get("maintenance_history") or []

    logger.info(f"[diagnose_node] Running LLM diagnosis for {equipment_id}")

    # Prepare context sections
    health_status_json = json.dumps(health_status, indent=2)
    technical_docs_text = "\n\n".join(retrieved_docs) if retrieved_docs else "No technical documentation available."
    maintenance_history_text = "\n\n".join(maintenance_history) if maintenance_history else "No maintenance history available."

    prompt = f"""You are an expert industrial equipment maintenance AI. Analyze the following equipment data and provide a diagnosis.

Equipment ID: {equipment_id}
Query: {user_query}

HEALTH STATUS:
{health_status_json}

TECHNICAL DOCUMENTATION:
{technical_docs_text}

MAINTENANCE HISTORY:
{maintenance_history_text}

Based on this information, provide your diagnosis. You MUST respond with ONLY valid JSON in this exact format:
{{
  "diagnosis": "detailed diagnosis text",
  "root_cause": "identified root cause",
  "recommended_action": "specific recommended action",
  "confidence_score": 0.85,
  "severity": "HIGH"
}}

severity must be exactly one of: LOW, MEDIUM, HIGH, CRITICAL
confidence_score must be between 0.0 and 1.0"""

    human_message = HumanMessage(content=prompt)

    # Default values in case of failure
    diagnosis = "Unable to perform diagnosis due to an error."
    root_cause = "Unknown"
    recommended_action = "Please consult a maintenance engineer."
    confidence_score = 0.5
    severity = "MEDIUM"
    ai_message = None

    try:
        llm = _get_llm()
        response = llm.invoke([human_message])
        raw_text = response.content if hasattr(response, "content") else str(response)
        ai_message = AIMessage(content=raw_text)

        # Attempt to parse JSON from the LLM response
        # Strip any markdown code fences if present
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            # Remove opening fence (```json or ```)
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        parsed = json.loads(cleaned)
        diagnosis = parsed.get("diagnosis", diagnosis)
        root_cause = parsed.get("root_cause", root_cause)
        recommended_action = parsed.get("recommended_action", recommended_action)
        confidence_score = float(parsed.get("confidence_score", confidence_score))
        severity = str(parsed.get("severity", severity)).upper()

        # Validate severity value
        if severity not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            logger.warning(f"[diagnose_node] Unexpected severity '{severity}', defaulting to MEDIUM")
            severity = "MEDIUM"

        # Clamp confidence score to [0.0, 1.0]
        confidence_score = max(0.0, min(1.0, confidence_score))

    except json.JSONDecodeError as e:
        logger.warning(
            f"[diagnose_node] Failed to parse LLM JSON response: {e}. "
            f"Using raw text as diagnosis."
        )
        # Use whatever raw text was returned as the diagnosis
        if ai_message:
            diagnosis = ai_message.content
        severity = "MEDIUM"
        confidence_score = 0.5
    except Exception as e:
        logger.error(f"[diagnose_node] LLM invocation failed: {e}")
        severity = "MEDIUM"
        confidence_score = 0.5

    agent_steps.append(
        f"Diagnosis complete: {severity} severity, confidence={confidence_score:.0%}"
    )

    updated_messages = [human_message]
    if ai_message:
        updated_messages.append(ai_message)

    return {
        "diagnosis": diagnosis,
        "root_cause": root_cause,
        "recommended_action": recommended_action,
        "confidence_score": confidence_score,
        "severity": severity,
        "agent_steps": agent_steps,
        "messages": updated_messages,
    }


def work_order_node(state: AgentState) -> dict:
    """Node 4: Create work order for HIGH/CRITICAL faults."""
    equipment_id = state["equipment_id"]
    agent_steps = list(state.get("agent_steps") or [])

    diagnosis = state.get("diagnosis") or "Fault detected — details unavailable."
    severity = state.get("severity") or "HIGH"
    recommended_action = state.get("recommended_action") or "Inspect and service equipment."

    logger.info(
        f"[work_order_node] Creating work order for {equipment_id}, severity={severity}"
    )

    try:
        raw_result = create_work_order.invoke(
            {
                "equipment_id": equipment_id,
                "fault_description": diagnosis,
                "severity": severity,
                "recommended_action": recommended_action,
                "created_by_user_id": 1,
            }
        )
        work_order_data = json.loads(raw_result)
        work_order_id = work_order_data.get("work_order_id", "UNKNOWN")
    except Exception as e:
        logger.error(f"[work_order_node] Failed to create work order: {e}")
        work_order_id = "ERROR"
        work_order_data = {
            "work_order_id": work_order_id,
            "equipment_id": equipment_id,
            "error": str(e),
        }

    agent_steps.append(f"Work order created: {work_order_id}")

    return {
        "work_order_created": True,
        "work_order_id": work_order_id,
        "work_order_data": work_order_data,
        "agent_steps": agent_steps,
    }


def respond_node(state: AgentState) -> dict:
    """Node 5: Compile final response."""
    agent_steps = list(state.get("agent_steps") or [])
    n_steps = len(agent_steps)

    agent_steps.append(f"Analysis complete. {n_steps} steps executed.")

    logger.info(f"[respond_node] Workflow complete — {n_steps} steps executed.")

    return {
        "agent_steps": agent_steps,
    }
