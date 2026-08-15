import random
from datetime import datetime, timezone
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.auth.dependencies import require_engineer
from src.database import get_db
from src.models.schemas import EquipmentListItem, HealthStatusResponse, SensorReadings
from src.models.user import User
from src.models.work_order import DiagnosticSession

router = APIRouter(prefix="/api/equipment", tags=["equipment"])

# All equipment IDs in the system
_TURBOFAN_IDS = [f"Engine-{i:02d}" for i in range(1, 21)]
_PUMP_IDS = [f"Pump-{i:02d}" for i in range(1, 16)]
_COMPRESSOR_IDS = [f"Comp-{i:02d}" for i in range(1, 16)]
ALL_EQUIPMENT = _TURBOFAN_IDS + _PUMP_IDS + _COMPRESSOR_IDS


def _get_equipment_type(equipment_id: str) -> str:
    if equipment_id.startswith("Engine"):
        return "turbofan"
    if equipment_id.startswith("Pump"):
        return "pump"
    return "compressor"


def _get_turbofan_health(equipment_id: str) -> dict:
    """
    Return health data for turbofan engines backed by NASA CMAPSS data.
    Falls back to simulation if CMAPSS data not yet loaded.
    """
    try:
        from src.data.cmapss_processor import cmapss
        if not cmapss._loaded:
            cmapss.load()
        snapshot = cmapss.get_snapshot(equipment_id)
        if snapshot:
            sr = snapshot.sensor_readings
            sensor_readings = SensorReadings(
                temperature=sr.get("T30"),          # HPC outlet temp (key degradation indicator)
                vibration=None,                      # not in CMAPSS
                pressure=sr.get("Ps30"),             # static pressure at HPC
                speed_rpm=sr.get("Nf"),              # fan speed
                oil_level=None,
            )
            return {
                "health_score": snapshot.health_score,
                "rul": snapshot.rul,
                "status": snapshot.status,
                "sensor_readings": sensor_readings,
                "cycle": snapshot.current_cycle,
                "max_cycle": snapshot.max_cycle,
                "all_sensors": snapshot.sensor_readings,
            }
    except Exception:
        pass  # fall through to simulation

    return _simulate_health_fallback(equipment_id)


def _simulate_health_fallback(equipment_id: str) -> dict:
    """Deterministic simulation fallback when CMAPSS data unavailable."""
    seed = hash(equipment_id) % 10000
    rng = random.Random(seed)
    eq_type = _get_equipment_type(equipment_id)
    health_score = round(rng.uniform(20.0, 98.0), 1)
    rul = rng.randint(50, 2000)
    if health_score < 30:
        status_str = "CRITICAL"
    elif health_score < 60:
        status_str = "WARNING"
    else:
        status_str = "OK"

    if eq_type == "turbofan":
        sensor_readings = SensorReadings(
            temperature=round(rng.uniform(450.0, 650.0), 1),
            vibration=round(rng.uniform(0.1, 1.5), 3),
            pressure=round(rng.uniform(200.0, 350.0), 1),
            speed_rpm=round(rng.uniform(8000.0, 12000.0), 0),
        )
    elif eq_type == "pump":
        sensor_readings = SensorReadings(
            temperature=round(rng.uniform(40.0, 90.0), 1),
            vibration=round(rng.uniform(0.5, 6.0), 3),
            pressure=round(rng.uniform(50.0, 250.0), 1),
            speed_rpm=round(rng.uniform(1400.0, 3600.0), 0),
        )
    else:
        sensor_readings = SensorReadings(
            temperature=round(rng.uniform(60.0, 120.0), 1),
            vibration=round(rng.uniform(0.5, 5.0), 3),
            pressure=round(rng.uniform(100.0, 275.0), 1),
        )
    return {
        "health_score": health_score,
        "rul": rul,
        "status": status_str,
        "sensor_readings": sensor_readings,
        "all_sensors": {},
    }


def _get_health(equipment_id: str) -> dict:
    """Dispatch to CMAPSS (turbofan) or simulation (pump/compressor)."""
    if equipment_id.startswith("Engine-"):
        return _get_turbofan_health(equipment_id)
    return _simulate_health_fallback(equipment_id)


@router.get("/", response_model=List[EquipmentListItem])
def list_equipment(
    _user: Annotated[User, Depends(require_engineer)],
    db: Session = Depends(get_db),
):
    result = []
    now = datetime.now(timezone.utc)
    for eq_id in ALL_EQUIPMENT:
        health = _get_health(eq_id)
        result.append(
            EquipmentListItem(
                equipment_id=eq_id,
                equipment_type=_get_equipment_type(eq_id),
                health_score=health["health_score"],
                rul=health["rul"],
                status=health["status"],
                last_fault_code=None,
                last_updated=now,
            )
        )
    # Sort by status priority: CRITICAL first, then WARNING, then OK
    priority = {"CRITICAL": 0, "WARNING": 1, "OK": 2}
    result.sort(key=lambda x: priority.get(x.status, 3))
    return result


@router.get("/{equipment_id}/health", response_model=HealthStatusResponse)
def get_equipment_health(
    equipment_id: str,
    _user: Annotated[User, Depends(require_engineer)],
):
    if equipment_id not in ALL_EQUIPMENT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment '{equipment_id}' not found",
        )
    health = _get_health(equipment_id)
    return HealthStatusResponse(
        equipment_id=equipment_id,
        health_score=health["health_score"],
        rul=health["rul"],
        status=health["status"],
        sensor_readings=health["sensor_readings"],
        last_updated=datetime.now(timezone.utc),
    )


@router.get("/{equipment_id}/sensors")
def get_equipment_sensors(
    equipment_id: str,
    _user: Annotated[User, Depends(require_engineer)],
):
    """Return all raw CMAPSS sensor readings for turbofan engines."""
    if equipment_id not in ALL_EQUIPMENT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment '{equipment_id}' not found",
        )
    health = _get_health(equipment_id)
    return {
        "equipment_id": equipment_id,
        "equipment_type": _get_equipment_type(equipment_id),
        "current_cycle": health.get("cycle"),
        "max_cycle": health.get("max_cycle"),
        "rul": health["rul"],
        "health_score": health["health_score"],
        "status": health["status"],
        "sensors": health.get("all_sensors", {}),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{equipment_id}/history")
def get_equipment_history(
    equipment_id: str,
    _user: Annotated[User, Depends(require_engineer)],
    db: Session = Depends(get_db),
):
    if equipment_id not in ALL_EQUIPMENT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment '{equipment_id}' not found",
        )
    sessions = (
        db.query(DiagnosticSession)
        .filter(DiagnosticSession.equipment_id == equipment_id)
        .order_by(DiagnosticSession.created_at.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "session_id": s.session_id,
            "query": s.query,
            "diagnosis": s.diagnosis,
            "confidence_score": s.confidence_score,
            "work_order_id": s.work_order_id,
            "created_at": s.created_at,
        }
        for s in sessions
    ]
