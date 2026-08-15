import math
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.auth.dependencies import require_engineer
from src.database import get_db
from src.models.schemas import DiagnosticRequest, DiagnosticResponse, PaginatedResponse
from src.models.user import User
from src.models.work_order import DiagnosticSession

router = APIRouter(prefix="/api/diagnostic", tags=["diagnostic"])


@router.post("/run", response_model=DiagnosticResponse)
def run_diagnostic(
    body: DiagnosticRequest,
    current_user: Annotated[User, Depends(require_engineer)],
    db: Session = Depends(get_db),
):
    """Run full LangGraph diagnostic workflow for the given equipment and query."""
    from src.agents.graph import run_diagnostic as _run

    thread_id = str(uuid.uuid4())
    try:
        result = _run(
            equipment_id=body.equipment_id,
            query=body.query,
            user_id=current_user.id,
            thread_id=thread_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Diagnostic workflow failed: {str(e)}",
        )

    # Persist session to DB
    session_id = str(uuid.uuid4())
    session = DiagnosticSession(
        session_id=session_id,
        user_id=current_user.id,
        equipment_id=body.equipment_id,
        query=body.query,
        diagnosis=result.get("diagnosis"),
        root_cause=result.get("root_cause"),
        recommended_action=result.get("recommended_action"),
        confidence_score=result.get("confidence_score"),
        work_order_id=result.get("work_order_id"),
        sources_used=result.get("retrieved_docs", []),
        agent_steps=result.get("agent_steps", []),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return DiagnosticResponse(
        session_id=session.session_id,
        equipment_id=session.equipment_id,
        diagnosis=session.diagnosis,
        root_cause=session.root_cause,
        recommended_action=session.recommended_action,
        confidence_score=session.confidence_score,
        severity=result.get("severity"),
        work_order_id=session.work_order_id,
        work_order_created=result.get("work_order_created", False),
        sources_used=session.sources_used if session.sources_used else [],
        agent_steps=session.agent_steps if session.agent_steps else [],
        created_at=session.created_at,
    )


@router.get("/history", response_model=PaginatedResponse[DiagnosticResponse])
def get_diagnostic_history(
    _user: Annotated[User, Depends(require_engineer)],
    db: Session = Depends(get_db),
    equipment_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    query = db.query(DiagnosticSession)
    if equipment_id:
        query = query.filter(DiagnosticSession.equipment_id == equipment_id)

    total = query.count()
    items = (
        query.order_by(DiagnosticSession.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return PaginatedResponse(
        items=[
            DiagnosticResponse(
                session_id=s.session_id,
                equipment_id=s.equipment_id,
                diagnosis=s.diagnosis,
                root_cause=s.root_cause,
                recommended_action=s.recommended_action,
                confidence_score=s.confidence_score,
                severity=None,
                work_order_id=s.work_order_id,
                work_order_created=bool(s.work_order_id),
                sources_used=s.sources_used if s.sources_used else [],
                agent_steps=s.agent_steps if s.agent_steps else [],
                created_at=s.created_at,
            )
            for s in items
        ],
        total=total,
        page=page,
        limit=limit,
        pages=math.ceil(total / limit) if total else 0,
    )


@router.get("/{session_id}", response_model=DiagnosticResponse)
def get_diagnostic_session(
    session_id: str,
    _user: Annotated[User, Depends(require_engineer)],
    db: Session = Depends(get_db),
):
    session = (
        db.query(DiagnosticSession)
        .filter(DiagnosticSession.session_id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic session not found",
        )
    return DiagnosticResponse(
        session_id=session.session_id,
        equipment_id=session.equipment_id,
        diagnosis=session.diagnosis,
        root_cause=session.root_cause,
        recommended_action=session.recommended_action,
        confidence_score=session.confidence_score,
        severity=None,
        work_order_id=session.work_order_id,
        work_order_created=bool(session.work_order_id),
        sources_used=session.sources_used if session.sources_used else [],
        agent_steps=session.agent_steps if session.agent_steps else [],
        created_at=session.created_at,
    )
