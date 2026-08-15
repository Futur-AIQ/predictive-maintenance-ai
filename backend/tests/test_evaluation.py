import pytest
from unittest.mock import patch, MagicMock
import tempfile
import json
import os


def test_rag_metrics_structure():
    """Evaluation report must contain all 4 RAGAS metric keys with valid float values."""
    from src.evaluation.rag_evaluator import _compute_simple_metrics, _EVAL_QUESTIONS

    # Minimal mock answers and contexts
    answers = ["The vibration limit is 0.5 in/s for normal operation."] * len(_EVAL_QUESTIONS)
    contexts = [["Vibration limits: Normal <0.5 in/s, Warning 0.5-1.0 in/s, Critical >1.0 in/s"]] * len(
        _EVAL_QUESTIONS
    )

    metrics = _compute_simple_metrics(_EVAL_QUESTIONS, answers, contexts)

    assert "faithfulness" in metrics
    assert "answer_relevancy" in metrics
    assert "context_precision" in metrics
    assert "context_recall" in metrics

    for key, val in metrics.items():
        assert isinstance(val, float), f"{key} should be float, got {type(val)}"
        assert 0.0 <= val <= 1.0, f"{key}={val} is out of [0, 1] range"


def test_evaluation_report_saved_to_disk():
    """run_evaluation should persist a JSON report file."""
    mock_ragas_result = {
        "faithfulness": 0.85,
        "answer_relevancy": 0.80,
        "context_precision": 0.78,
        "context_recall": 0.82,
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        with (
            patch("src.evaluation.rag_evaluator._retrieve_context") as mock_ctx,
            patch("src.evaluation.rag_evaluator._generate_answer") as mock_ans,
            patch("ragas.evaluate", return_value=mock_ragas_result),
        ):
            from src.evaluation.rag_evaluator import _EVAL_QUESTIONS

            mock_ctx.return_value = ["Sample context about bearing failure and vibration limits"]
            mock_ans.return_value = "The vibration limit is 0.5 in/s"

            from src.evaluation.rag_evaluator import run_evaluation

            report = run_evaluation(processed_data_dir=tmpdir)

            # Report file should exist
            report_path = os.path.join(tmpdir, "latest_evaluation.json")
            assert os.path.exists(report_path)

            with open(report_path) as f:
                saved = json.load(f)

            assert "faithfulness" in saved
            assert "timestamp" in saved
            assert saved["sample_count"] == len(_EVAL_QUESTIONS)


def test_evaluation_endpoint_admin_only(client, engineer_token, admin_token):
    """GET /api/evaluation/run must return 403 for engineers and allow admins."""
    # Engineer should be denied
    resp = client.get(
        "/api/evaluation/run",
        headers={"Authorization": f"Bearer {engineer_token}"},
    )
    assert resp.status_code == 403

    # Admin would trigger actual evaluation — just check auth passes (mock the evaluation)
    with (
        patch("src.api.routers.evaluation.run_evaluation") as mock_eval,
    ):
        mock_eval.return_value = {
            "faithfulness": 0.85,
            "answer_relevancy": 0.80,
            "context_precision": 0.78,
            "context_recall": 0.82,
            "timestamp": "2025-01-01T00:00:00+00:00",
            "sample_count": 5,
        }
        resp = client.get(
            "/api/evaluation/run",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "faithfulness" in data
        assert "answer_relevancy" in data


def test_latest_evaluation_not_found(client, engineer_token):
    """GET /api/evaluation/latest returns 404 when no report exists yet."""
    with patch("src.api.routers.evaluation.load_latest_evaluation") as mock_load:
        mock_load.return_value = None
        resp = client.get(
            "/api/evaluation/latest",
            headers={"Authorization": f"Bearer {engineer_token}"},
        )
        assert resp.status_code == 404
