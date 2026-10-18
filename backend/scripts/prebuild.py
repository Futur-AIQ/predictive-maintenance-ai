#!/usr/bin/env python
"""
Build-time warm-up for hosted deployments (e.g. Render's build step).

Downloads the embedding model (and the cross-encoder, if enabled) into the
Hugging Face cache and ingests data/raw into ChromaDB, so the first boot of
the web service only has to load them instead of building them.

Usage (from backend/):
    python scripts/prebuild.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

from loguru import logger  # noqa: E402

from src.config import settings  # noqa: E402
from src.data_ingestion import run_ingestion  # noqa: E402
from src.rag.vector_store import vector_store  # noqa: E402


def main() -> None:
    run_ingestion(settings.raw_data_dir)
    # Ingestion is skipped when the index already exists, so load the
    # embedding model explicitly to make sure it is in the cache
    vector_store.embeddings.embed_query("warm-up")

    if settings.enable_reranker:
        from src.rag.retriever import _get_cross_encoder

        _get_cross_encoder()

    logger.info("Prebuild complete.")


if __name__ == "__main__":
    main()
