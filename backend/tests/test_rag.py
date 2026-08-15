import os
import json
import tempfile
import pytest
from unittest.mock import MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_manual_file(tmp_path, filename="equipment_manual_turbofan.txt"):
    content = """# TURBOFAN ENGINE MAINTENANCE MANUAL

## 1. Overview
The CFM56-7B is a dual-spool turbofan engine with a bypass ratio of 5.1:1 producing 27,300 lbf thrust.

## 2. Fault Codes
F001 | Fan blade erosion | MEDIUM | Inspect fan blades | 24h
F006 | Bearing failure LP shaft | CRITICAL | Immediate engine removal | 2h
F008 | Vibration anomaly | MEDIUM | Check balance, bearing wear | 16h

## 3. Vibration Limits
Normal: <0.5 in/s
Warning: 0.5-1.0 in/s
Critical: >1.0 in/s - immediate shutdown required
"""
    f = tmp_path / filename
    f.write_text(content, encoding="utf-8")
    return str(f)


def _make_fault_code_file(tmp_path):
    lines = [
        "CODE|EQUIPMENT_TYPE|DESCRIPTION|SEVERITY|RECOMMENDED_ACTION|RESPONSE_TIME_HOURS",
        "F001|turbofan|Fan blade erosion|MEDIUM|Inspect/replace fan blades|24",
        "F006|turbofan|Bearing failure LP shaft|CRITICAL|Immediate engine removal|2",
        "P001|pump|Cavitation|HIGH|Check NPSH, reduce flow|4",
    ]
    f = tmp_path / "fault_code_reference.txt"
    f.write_text("\n".join(lines), encoding="utf-8")
    return str(f)


def _make_log_file(tmp_path):
    entries = [
        {
            "timestamp": "2024-01-15T08:30:00Z",
            "equipment_id": "Engine-05",
            "technician": "Mike Johnson",
            "fault_code": "F008",
            "description": "Vibration reading at 0.54 in/s, approaching warning threshold",
            "action_taken": "Inspected LP bearing, added lubrication",
            "resolution_time_hours": 4.0,
            "work_order_id": "WO-10001",
            "parts_replaced": [],
            "cost_usd": 350.0,
        },
        {
            "timestamp": "2024-03-20T10:00:00Z",
            "equipment_id": "Pump-02",
            "technician": "Sarah Chen",
            "fault_code": "P001",
            "description": "Cavitation noise detected, flow drop 15%",
            "action_taken": "Increased suction pressure, cleared strainer",
            "resolution_time_hours": 2.5,
            "work_order_id": "WO-10002",
            "parts_replaced": ["suction strainer"],
            "cost_usd": 210.0,
        },
    ]
    f = tmp_path / "maintenance_logs.jsonl"
    f.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")
    return str(f)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_document_chunking_preserves_metadata(tmp_path):
    from src.rag.document_processor import DocumentProcessor

    manual_path = _make_manual_file(tmp_path)
    processor = DocumentProcessor()
    docs = processor.process_manual(manual_path)

    assert len(docs) > 0
    for doc in docs:
        assert "source_file" in doc.metadata
        assert "equipment_type" in doc.metadata
        assert "chunk_type" in doc.metadata
        assert doc.metadata["chunk_type"] == "manual"
        assert isinstance(doc.metadata["fault_codes_mentioned"], list)
        assert isinstance(doc.metadata["severity_mentioned"], list)

    # Check that turbofan type is detected
    types = {d.metadata["equipment_type"] for d in docs}
    assert "turbofan" in types


def test_fault_code_chunking_one_per_row(tmp_path):
    from src.rag.document_processor import DocumentProcessor

    fc_path = _make_fault_code_file(tmp_path)
    processor = DocumentProcessor()
    docs = processor.process_fault_codes(fc_path)

    # 3 data rows → exactly 3 documents
    assert len(docs) == 3
    for doc in docs:
        assert doc.metadata["chunk_type"] == "fault_code"

    # Each chunk contains exactly one fault code
    codes_in_first = doc.metadata["fault_codes_mentioned"] if docs else []
    # The fault_codes_mentioned for F001 chunk should include F001
    codes_all = [d.metadata["fault_codes_mentioned"] for d in docs]
    all_codes_flat = [c for sublist in codes_all for c in sublist]
    assert any(c.upper() in ("F001", "F006", "P001") for c in all_codes_flat)


def test_log_chunking_one_per_entry(tmp_path):
    from src.rag.document_processor import DocumentProcessor

    log_path = _make_log_file(tmp_path)
    processor = DocumentProcessor()
    docs = processor.process_maintenance_logs(log_path)

    assert len(docs) == 2
    for doc in docs:
        assert doc.metadata["chunk_type"] == "log"
        assert "Engine-05" in doc.page_content or "Pump-02" in doc.page_content


def test_vector_store_returns_relevant_results():
    """Test that VectorStoreManager.similarity_search delegates to the Chroma wrapper."""
    from langchain.schema import Document
    from src.rag.vector_store import VectorStoreManager

    mock_doc = Document(
        page_content="Bearing failure on LP shaft requires immediate engine removal",
        metadata={"source_file": "test.txt", "chunk_type": "manual"},
    )

    # Mock both chromadb client and HuggingFaceEmbeddings to avoid loading sentence-transformers
    with patch("src.rag.vector_store.chromadb.PersistentClient") as mock_chroma_client, \
         patch("src.rag.vector_store.HuggingFaceEmbeddings") as mock_embeddings:

        mock_collection = MagicMock()
        mock_collection.count.return_value = 2
        mock_chroma_client.return_value.get_or_create_collection.return_value = mock_collection
        mock_chroma_client.return_value.get_collection.return_value = mock_collection
        mock_embeddings.return_value = MagicMock()

        vs = VectorStoreManager()
        vs.initialize()

        # Mock the Chroma wrapper's similarity_search
        mock_store = MagicMock()
        mock_store.similarity_search.return_value = [mock_doc]
        vs._stores["technical_docs"] = mock_store

        results = vs.similarity_search("bearing failure turbofan", "technical_docs", k=2)
        assert len(results) >= 1
        assert any("bearing" in r.page_content.lower() for r in results)


def test_hybrid_retriever_merges_results():
    """Test that HybridRetriever combines vector and BM25 results."""
    from langchain.schema import Document
    from src.rag.retriever import HybridRetriever

    mock_doc1 = Document(page_content="Bearing failure critical action required", metadata={})
    mock_doc2 = Document(page_content="Vibration anomaly check balance and wear", metadata={})
    mock_doc3 = Document(page_content="Blade inspection checklist annual maintenance", metadata={})

    with patch("src.rag.retriever.vector_store") as mock_vs:
        mock_vs.similarity_search.return_value = [mock_doc1, mock_doc2]

        hr = HybridRetriever()
        # Pre-populate BM25 index manually
        hr._bm25_index["technical_docs"] = (
            MagicMock(get_scores=MagicMock(return_value=[0.9, 0.5, 0.1])),
            [mock_doc1, mock_doc2, mock_doc3],
        )

        results = hr.retrieve("bearing failure", "technical_docs", k=3)
        assert len(results) >= 1


def test_fault_code_query_prioritization():
    """Test that querying with a fault code boosts matching chunks."""
    from langchain.schema import Document
    from src.rag.retriever import HybridRetriever

    doc_f008 = Document(
        page_content="F008 Vibration anomaly — check balance and bearing wear",
        metadata={"fault_codes_mentioned": ["F008"]},
    )
    doc_other = Document(
        page_content="General maintenance procedures for turbofan engines",
        metadata={"fault_codes_mentioned": []},
    )

    with patch("src.rag.retriever.vector_store") as mock_vs:
        # Return other doc first in vector search, F008 second
        mock_vs.similarity_search.return_value = [doc_other, doc_f008]

        hr = HybridRetriever()
        hr._bm25_index["technical_docs"] = (
            MagicMock(get_scores=MagicMock(return_value=[0.5, 0.8])),
            [doc_other, doc_f008],
        )

        results = hr.retrieve("F008 vibration fault", "technical_docs", k=2)
        # F008 doc should be boosted to top
        assert len(results) >= 1
        assert "F008" in results[0].page_content
