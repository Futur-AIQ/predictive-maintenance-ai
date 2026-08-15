import json
import random
import uuid
from datetime import datetime, timezone
from typing import Optional

from langchain_core.tools import tool
from loguru import logger

from src.config import settings
from src.rag.retriever import retriever


@tool
def retrieve_technical_documentation(query: str, equipment_type: Optional[str] = None) -> str:
    """Retrieve relevant technical documentation and fault code references for the given query."""
    try:
        docs = retriever.retrieve(query, "technical_docs", k=5)

        if not docs:
            return "No technical documentation found for the given query."

        results = []
        for doc in docs:
            # If equipment_type is provided, prioritise docs that match it by listing them first
            source = doc.metadata.get("source_file", "unknown")
            doc_eq_type = doc.metadata.get("equipment_type", "")
            fault_codes = doc.metadata.get("fault_codes_mentioned", [])
            severity = doc.metadata.get("severity_mentioned", [])

            meta_parts = [f"Source: {source}"]
            if doc_eq_type:
                meta_parts.append(f"Equipment Type: {doc_eq_type}")
            if fault_codes:
                meta_parts.append(f"Fault Codes: {', '.join(fault_codes)}")
            if severity:
                meta_parts.append(f"Severity: {', '.join(severity)}")

            entry = "\n".join(meta_parts) + f"\nContent: {doc.page_content}\n---"
            results.append((doc_eq_type, entry))

        # If equipment_type provided, sort so matching docs appear first
        if equipment_type:
            eq_lower = equipment_type.lower()
            results.sort(key=lambda x: 0 if eq_lower in x[0].lower() else 1)

        return "\n".join(entry for _, entry in results)

    except Exception as e:
        logger.error(f"Error retrieving technical documentation: {e}")
        return f"Error retrieving technical documentation: {str(e)}"


@tool
def retrieve_maintenance_history(equipment_id: str, fault_code: Optional[str] = None) -> str:
    """Retrieve past maintenance logs for the specified equipment."""
    try:
        # Build a targeted query combining equipment_id and optional fault_code
        query_parts = [f"equipment {equipment_id} maintenance history"]
        if fault_code:
            query_parts.append(f"fault code {fault_code}")
        query = " ".join(query_parts)

        docs = retriever.retrieve(query, "maintenance_history", k=5)

        if not docs:
            return f"No maintenance history found for equipment {equipment_id}."

        # Filter to docs that actually mention this equipment_id in their content
        filtered = [
            doc for doc in docs
            if equipment_id.lower() in doc.page_content.lower()
        ]

        # Fall back to all retrieved docs if none mention the equipment_id directly
        if not filtered:
            filtered = docs

        results = []
        for doc in filtered:
            source = doc.metadata.get("source_file", "unknown")
            fault_codes_mentioned = doc.metadata.get("fault_codes_mentioned", [])

            meta_parts = [f"Source: {source}"]
            if fault_codes_mentioned:
                meta_parts.append(f"Fault Codes: {', '.join(fault_codes_mentioned)}")

            entry = "\n".join(meta_parts) + f"\nContent: {doc.page_content}\n---"
            results.append(entry)

        return "\n".join(results)

    except Exception as e:
        logger.error(f"Error retrieving maintenance history: {e}")
        return f"Error retrieving maintenance history: {str(e)}"


@tool
def get_equipment_health_status(equipment_id: str) -> str:
    """Get current health status and sensor readings for equipment."""
    eq_upper = equipment_id.upper()
    if eq_upper.startswith("ENGINE-"):
        equipment_type = "turbofan"
    elif eq_upper.startswith("PUMP-"):
        equipment_type = "pump"
    elif eq_upper.startswith("COMP-"):
        equipment_type = "compressor"
    else:
        equipment_type = "unknown"

    # Turbofan engines: use NASA CMAPSS data for realistic sensor values
    if equipment_type == "turbofan":
        try:
            from src.data.cmapss_processor import cmapss
            if not cmapss._loaded:
                cmapss.load()
            snapshot = cmapss.get_snapshot(equipment_id)
            if snapshot:
                sr = snapshot.sensor_readings
                result = {
                    "equipment_id": equipment_id,
                    "equipment_type": equipment_type,
                    "health_score": snapshot.health_score,
                    "rul": snapshot.rul,
                    "status": snapshot.status,
                    "current_cycle": snapshot.current_cycle,
                    "max_cycle": snapshot.max_cycle,
                    "sensor_readings": {
                        "T30": sr.get("T30"),          # HPC outlet temp (key degradation indicator)
                        "T50": sr.get("T50"),          # LPT outlet temp
                        "Ps30": sr.get("Ps30"),        # Static pressure at HPC (decreases with degradation)
                        "phi": sr.get("phi"),           # Fuel-air ratio (increases with degradation)
                        "BPR": sr.get("BPR"),           # Bypass ratio (decreases)
                        "W31": sr.get("W31"),           # HPT coolant bleed (decreases)
                        "W32": sr.get("W32"),           # LPT coolant bleed (decreases)
                        "Nf": sr.get("Nf"),             # Fan speed (rpm)
                        "Nc": sr.get("Nc"),             # Core speed (rpm)
                        "P30": sr.get("P30"),           # Total pressure at HPC outlet (decreases)
                        "htBleed": sr.get("htBleed"),   # Bleed enthalpy (decreases)
                    },
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }
                return json.dumps(result)
        except Exception as e:
            logger.warning(f"CMAPSS data unavailable for {equipment_id}, falling back to simulation: {e}")

    # Fallback: deterministic simulation for pumps, compressors, and turbofan fallback
    rng = random.Random(hash(equipment_id) % 10000)
    health_score = rng.randint(10, 100)
    rul = int(health_score * rng.uniform(1.5, 3.5))

    if health_score < 30:
        status = "CRITICAL"
    elif health_score < 60:
        status = "WARNING"
    else:
        status = "OK"

    degradation_factor = health_score / 100.0
    vibration_base = rng.uniform(0.5, 1.5) + (1.0 - degradation_factor) * 4.0

    if equipment_type == "pump":
        sensor_readings = {
            "flow_rate_lpm": round(150.0 * degradation_factor * rng.uniform(0.85, 1.05), 2),
            "pressure_bar": round(8.5 * degradation_factor * rng.uniform(0.88, 1.08), 2),
            "vibration_mm_s": round(vibration_base, 3),
            "temperature_celsius": round(
                65.0 + (1.0 - degradation_factor) * rng.uniform(5.0, 35.0), 2
            ),
        }
    elif equipment_type == "compressor":
        sensor_readings = {
            "discharge_pressure_bar": round(
                12.0 * degradation_factor * rng.uniform(0.87, 1.05), 2
            ),
            "temperature_celsius": round(
                90.0 + (1.0 - degradation_factor) * rng.uniform(10.0, 50.0), 2
            ),
            "vibration_mm_s": round(vibration_base, 3),
        }
    else:
        sensor_readings = {
            "T30": round(550.0 + (1.0 - degradation_factor) * rng.uniform(20.0, 80.0), 2),
            "Ps30": round(47.5 - (1.0 - degradation_factor) * rng.uniform(1.0, 3.0), 2),
            "vibration_mm_s": round(vibration_base, 3),
            "speed_rpm": round(12000.0 * degradation_factor * rng.uniform(0.92, 1.02), 1),
        }

    result = {
        "equipment_id": equipment_id,
        "equipment_type": equipment_type,
        "health_score": health_score,
        "rul": rul,
        "status": status,
        "sensor_readings": sensor_readings,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(result)


@tool
def create_work_order(
    equipment_id: str,
    fault_description: str,
    severity: str,
    recommended_action: str,
    created_by_user_id: int = 1,
) -> str:
    """Create a work order in the database for high/critical severity faults."""
    # Import inside function to avoid circular imports at module load time
    from src.database import SessionLocal
    from src.models.work_order import WorkOrder, Severity, WorkOrderStatus

    db = SessionLocal()
    try:
        # Map severity string to Severity enum (case insensitive)
        severity_upper = severity.upper()
        try:
            severity_enum = Severity[severity_upper]
        except KeyError:
            severity_enum = Severity.MEDIUM
            logger.warning(
                f"Unknown severity '{severity}', defaulting to MEDIUM"
            )

        # Set priority_score based on severity
        priority_map = {
            Severity.CRITICAL: 1.0,
            Severity.HIGH: 0.8,
            Severity.MEDIUM: 0.5,
            Severity.LOW: 0.2,
        }
        priority_score = priority_map.get(severity_enum, 0.5)

        # Set estimated completion hours based on severity
        hours_map = {
            Severity.CRITICAL: 2.0,
            Severity.HIGH: 8.0,
            Severity.MEDIUM: 16.0,
            Severity.LOW: 24.0,
        }
        estimated_hours = hours_map.get(severity_enum, 16.0)

        work_order = WorkOrder(
            work_order_id=str(uuid.uuid4()),
            equipment_id=equipment_id,
            fault_description=fault_description,
            severity=severity_enum,
            status=WorkOrderStatus.OPEN,
            recommended_action=recommended_action,
            created_by=created_by_user_id,
            priority_score=priority_score,
            estimated_completion_hours=estimated_hours,
        )

        db.add(work_order)
        db.commit()
        db.refresh(work_order)

        logger.info(
            f"Work order created: {work_order.work_order_id} "
            f"for {equipment_id} severity={severity_enum.value}"
        )

        result = {
            "work_order_id": work_order.work_order_id,
            "equipment_id": work_order.equipment_id,
            "severity": work_order.severity.value,
            "status": work_order.status.value,
            "priority_score": work_order.priority_score,
            "estimated_completion_hours": work_order.estimated_completion_hours,
            "created_at": work_order.created_at.isoformat(),
        }
        return json.dumps(result)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create work order: {e}")
        # Return a minimal result so the agent can continue
        fallback_id = str(uuid.uuid4())
        return json.dumps({
            "work_order_id": fallback_id,
            "equipment_id": equipment_id,
            "severity": severity.upper(),
            "status": "OPEN",
            "error": str(e),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    finally:
        db.close()


@tool
def calculate_maintenance_priority(equipment_id: str, fault_code: str) -> str:
    """Calculate maintenance priority score for the equipment and fault code."""
    fault_upper = fault_code.upper().strip()

    # Determine base priority from fault code prefix and numeric value
    # F = turbofan faults, P = pump faults, C = compressor faults
    # Higher numeric suffix generally means more severe fault
    base_priority = 0.5
    rationale_parts = []

    if fault_upper:
        prefix = fault_upper[0] if fault_upper[0].isalpha() else ""
        numeric_part = "".join(ch for ch in fault_upper[1:] if ch.isdigit())
        numeric_val = int(numeric_part) if numeric_part else 0

        # Map fault code ranges to severity bands
        if numeric_val >= 400:
            # CRITICAL severity codes — compressor surge, turbine overspeed, etc.
            base_priority = random.uniform(0.9, 1.0)
            severity_label = "CRITICAL"
            rationale_parts.append(
                f"Fault code {fault_upper} (numeric {numeric_val}) maps to CRITICAL severity band (>=400)"
            )
        elif numeric_val >= 300:
            # HIGH severity
            base_priority = random.uniform(0.7, 0.8)
            severity_label = "HIGH"
            rationale_parts.append(
                f"Fault code {fault_upper} (numeric {numeric_val}) maps to HIGH severity band (300-399)"
            )
        elif numeric_val >= 200:
            # MEDIUM severity
            base_priority = random.uniform(0.4, 0.6)
            severity_label = "MEDIUM"
            rationale_parts.append(
                f"Fault code {fault_upper} (numeric {numeric_val}) maps to MEDIUM severity band (200-299)"
            )
        else:
            # LOW severity
            base_priority = random.uniform(0.1, 0.3)
            severity_label = "LOW"
            rationale_parts.append(
                f"Fault code {fault_upper} (numeric {numeric_val}) maps to LOW severity band (<200)"
            )

        # Equipment type modifier
        if prefix == "F":
            rationale_parts.append("Turbofan fault — safety-critical equipment type (+0.05 bonus)")
            base_priority = min(1.0, base_priority + 0.05)
        elif prefix == "C":
            rationale_parts.append("Compressor fault — high-impact equipment type (+0.03 bonus)")
            base_priority = min(1.0, base_priority + 0.03)
    else:
        severity_label = "MEDIUM"
        rationale_parts.append("No fault code provided; defaulting to MEDIUM priority")

    # Equipment-level recurring-issue bonus
    # Engine-05 and Engine-15 are known recurring problem units
    recurring_units = {"ENGINE-05", "ENGINE-15"}
    eq_upper = equipment_id.upper()
    if eq_upper in recurring_units:
        bonus = 0.1
        base_priority = min(1.0, base_priority + bonus)
        rationale_parts.append(
            f"{equipment_id} is a flagged recurring-issue unit — priority boosted by {bonus}"
        )

    # Map priority score to estimated hours for remediation
    if base_priority >= 0.9:
        estimated_hours = 2.0
    elif base_priority >= 0.7:
        estimated_hours = 8.0
    elif base_priority >= 0.4:
        estimated_hours = 16.0
    else:
        estimated_hours = 24.0

    result = {
        "priority_score": round(base_priority, 4),
        "estimated_hours": estimated_hours,
        "rationale": "; ".join(rationale_parts) if rationale_parts else "Standard priority calculation",
    }

    return json.dumps(result)
