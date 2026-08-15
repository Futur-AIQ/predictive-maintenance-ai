import math
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.auth.dependencies import get_current_user, require_admin, require_engineer
from src.database import get_db
from src.models.schemas import PaginatedResponse, WorkOrderResponse, WorkOrderStatusUpdate
from src.models.user import User
from src.models.work_order import Severity, WorkOrder, WorkOrderStatus

router = APIRouter(prefix="/api/workorders", tags=["workorders"])


@router.get("/", response_model=PaginatedResponse[WorkOrderResponse])
def list_work_orders(
    _user: Annotated[User, Depends(require_engineer)],
    db: Session = Depends(get_db),
    status_filter: Optional[WorkOrderStatus] = Query(None, alias="status"),
    severity_filter: Optional[Severity] = Query(None, alias="severity"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    query = db.query(WorkOrder)
    if status_filter:
        query = query.filter(WorkOrder.status == status_filter)
    if severity_filter:
        query = query.filter(WorkOrder.severity == severity_filter)

    total = query.count()
    items = (
        query.order_by(WorkOrder.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return PaginatedResponse(
        items=[WorkOrderResponse.model_validate(w) for w in items],
        total=total,
        page=page,
        limit=limit,
        pages=math.ceil(total / limit) if total else 0,
    )


@router.get("/{work_order_id}", response_model=WorkOrderResponse)
def get_work_order(
    work_order_id: str,
    _user: Annotated[User, Depends(require_engineer)],
    db: Session = Depends(get_db),
):
    wo = db.query(WorkOrder).filter(WorkOrder.work_order_id == work_order_id).first()
    if not wo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    return WorkOrderResponse.model_validate(wo)


@router.patch("/{work_order_id}/status", response_model=WorkOrderResponse)
def update_work_order_status(
    work_order_id: str,
    body: WorkOrderStatusUpdate,
    current_user: Annotated[User, Depends(require_engineer)],
    db: Session = Depends(get_db),
):
    wo = db.query(WorkOrder).filter(WorkOrder.work_order_id == work_order_id).first()
    if not wo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")

    wo.status = body.status
    wo.updated_at = datetime.now(timezone.utc)
    if body.status in (WorkOrderStatus.RESOLVED, WorkOrderStatus.CLOSED):
        wo.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(wo)
    return WorkOrderResponse.model_validate(wo)


@router.delete("/{work_order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_order(
    work_order_id: str,
    _admin: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    wo = db.query(WorkOrder).filter(WorkOrder.work_order_id == work_order_id).first()
    if not wo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    db.delete(wo)
    db.commit()
