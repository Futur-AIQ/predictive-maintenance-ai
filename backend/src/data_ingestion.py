from loguru import logger

from src.rag.document_processor import DocumentProcessor
from src.rag.vector_store import vector_store


def run_ingestion(raw_data_dir: str = "./data/raw") -> None:
    """
    Orchestrates the full RAG ingestion pipeline:

    1. Initialise the vector store (ChromaDB + embeddings).
    2. Skip if both collections are already populated.
    3. Process raw data files via :class:`DocumentProcessor`.
    4. Ingest any collection that is still empty.
    5. Log final statistics.
    """
    vector_store.initialize()

    stats = vector_store.get_stats()
    if (
        stats["technical_docs_count"] > 0
        and stats["maintenance_history_count"] > 0
    ):
        logger.info(
            f"Collections already populated: {stats}. Skipping ingestion."
        )
        return

    processor = DocumentProcessor()
    technical_docs, maintenance_history = processor.process_all(raw_data_dir)

    if not vector_store.is_populated("technical_docs"):
        logger.info(f"Ingesting {len(technical_docs)} technical documents...")
        vector_store.add_documents(technical_docs, "technical_docs")

    if not vector_store.is_populated("maintenance_history"):
        logger.info(
            f"Ingesting {len(maintenance_history)} maintenance log entries..."
        )
        vector_store.add_documents(maintenance_history, "maintenance_history")

    final_stats = vector_store.get_stats()
    logger.info(f"Ingestion complete: {final_stats}")
