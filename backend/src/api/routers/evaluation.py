from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.dependencies import require_admin, require_engineer
from src.config import settings
from src.evaluation.rag_evaluator import load_latest_evaluation, run_evaluation
from src.models.schemas import EvaluationReport
from src.models.user import User

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("/run", response_model=EvaluationReport)
def run_rag_evaluation(_admin: Annotated[User, Depends(require_admin)]):
    """Run RAGAS evaluation suite (admin only). May take 1-2 minutes."""
    try:
        report = run_evaluation(settings.processed_data_dir)
        return EvaluationReport(
            faithfulness=report["faithfulness"],
            answer_relevancy=report["answer_relevancy"],
            context_precision=report["context_precision"],
            context_recall=report["context_recall"],
            timestamp=datetime.fromisoformat(report["timestamp"]),
            sample_count=report.get("sample_count", 0),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}",
        )


@router.get("/latest", response_model=EvaluationReport)
def get_latest_evaluation(_user: Annotated[User, Depends(require_engineer)]):
    """Return the most recent saved evaluation report."""
    report = load_latest_evaluation(settings.processed_data_dir)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evaluation report found. Run /api/evaluation/run first.",
        )
    return EvaluationReport(
        faithfulness=report["faithfulness"],
        answer_relevancy=report["answer_relevancy"],
        context_precision=report["context_precision"],
        context_recall=report["context_recall"],
        timestamp=datetime.fromisoformat(report["timestamp"]),
        sample_count=report.get("sample_count", 0),
    )
