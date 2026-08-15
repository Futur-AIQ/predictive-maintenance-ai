import pytest
from unittest.mock import MagicMock, patch


def _make_mock_llm_response(severity: str = "CRITICAL", confidence: float = 0.92):
    mock_response = MagicMock()
    mock_response.content = (
        f'{{"diagnosis": "Bearing wear detected on LP shaft", '
        f'"root_cause": "Insufficient lubrication leading to metal fatigue", '
        f'"recommended_action": "Immediate engine removal and bearing replacement", '
        f'"confidence_score": {confidence}, '
        f'"severity": "{severity}"}}'
    )
    return mock_response


@pytest.fixture
def patched_retriever():
    from langchain.schema import Document
    mock_doc = Document(
        page_content="F006 Bearing failure LP shaft CRITICAL immediate engine removal 2h",
        metadata={"source_file": "turbofan_manual.txt", "chunk_type": "manual"},
    )
    with patch("src.agents.tools.retriever") as mock_ret:
        mock_ret.retrieve.return_value = [mock_doc]
        yield mock_ret


@pytest.fixture
def patched_llm_critical():
    with patch("src.agents.nodes._get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_mock_llm_response("CRITICAL", 0.95)
        mock_get_llm.return_value = mock_llm
        yield mock_llm


@pytest.fixture
def patched_llm_low():
    with patch("src.agents.nodes._get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_mock_llm_response("LOW", 0.70)
        mock_get_llm.return_value = mock_llm
        yield mock_llm


def test_langgraph_workflow_critical_fault(patched_retriever, patched_llm_critical, db_session):
    """CRITICAL fault → agent creates work order automatically."""
    from src.agents.graph import run_diagnostic

    result = run_diagnostic(
        equipment_id="Engine-05",
        query="vibration reading 1.2 in/s bearing noise",
    )

    assert result["severity"] == "CRITICAL"
    assert result["confidence_score"] >= 0.9
    assert result["diagnosis"] is not None
    assert result["work_order_created"] is True
    assert result["work_order_id"] is not None
    assert len(result["agent_steps"]) >= 4


def test_langgraph_workflow_low_severity_no_work_order(patched_retriever, patched_llm_low):
    """LOW severity → no work order should be created."""
    from src.agents.graph import run_diagnostic

    result = run_diagnostic(
        equipment_id="Pump-03",
        query="slight noise during startup, normal by operating hours",
    )

    assert result["severity"] == "LOW"
    assert result["work_order_created"] is False
    assert result["work_order_id"] is None


def test_work_order_persisted_to_db(patched_retriever, patched_llm_critical):
    """Verify work order is saved to SQLite after CRITICAL diagnosis."""
    from src.agents.graph import run_diagnostic
    from src.database import SessionLocal
    from src.models.work_order import WorkOrder

    result = run_diagnostic(
        equipment_id="Engine-15",
        query="F006 bearing failure detected",
    )

    assert result["work_order_created"] is True
    wo_id = result["work_order_id"]
    assert wo_id is not None

    # Query the DB that tools.py writes to (uses src.database.SessionLocal)
    db = SessionLocal()
    try:
        wo = db.query(WorkOrder).filter(WorkOrder.work_order_id == wo_id).first()
        assert wo is not None
        assert wo.equipment_id == "Engine-15"
        assert wo.severity.value == "CRITICAL"
    finally:
        db.close()


def test_graceful_degradation_on_api_failure(patched_retriever):
    """Agent should not crash when LLM raises an exception."""
    with patch("src.agents.nodes._get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = RuntimeError("LLM service unavailable")
        mock_get_llm.return_value = mock_llm

        from src.agents.graph import run_diagnostic

        # Should not raise — graceful degradation
        result = run_diagnostic(
            equipment_id="Comp-01",
            query="pressure drop in intercooler",
        )

        # Even with LLM failure, state should have defaults
        assert result.get("severity") is not None or result.get("error") is not None
        assert isinstance(result.get("agent_steps", []), list)
