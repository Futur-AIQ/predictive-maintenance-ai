from typing import Any, List

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain.schema import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from loguru import logger

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma  # type: ignore[no-redef]

from src.config import settings


def _sanitize_metadata(metadata: dict) -> dict:
    """
    ChromaDB only accepts str, int, float, bool as metadata values.
    Convert any list/dict values to comma-separated strings.
    """
    sanitized = {}
    for key, value in metadata.items():
        if isinstance(value, list):
            sanitized[key] = ",".join(str(v) for v in value) if value else ""
        elif isinstance(value, dict):
            import json
            sanitized[key] = json.dumps(value)
        elif value is None:
            sanitized[key] = ""
        elif isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        else:
            sanitized[key] = str(value)
    return sanitized

# ---------------------------------------------------------------------------
# Collection names – used as constants throughout the module
# ---------------------------------------------------------------------------
_TECHNICAL_DOCS = "technical_docs"
_MAINTENANCE_HISTORY = "maintenance_history"


class VectorStoreManager:
    """
    Manages two ChromaDB-backed LangChain vector stores:

    - ``technical_docs``     – equipment manuals + fault-code reference
    - ``maintenance_history``– maintenance log entries

    The class is designed to be used as a module-level singleton (see
    ``vector_store`` at the bottom of this file).  Call
    :meth:`initialize` once before any other method.
    """

    def __init__(self) -> None:
        self._client: chromadb.PersistentClient | None = None
        self._embeddings: HuggingFaceEmbeddings | None = None
        # LangChain Chroma wrappers keyed by collection name
        self._stores: dict[str, Chroma] = {}

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """
        Create the ChromaDB persistent client and the HuggingFace embedding
        function.  Idempotent – safe to call multiple times.
        """
        if self._client is not None:
            logger.debug("VectorStoreManager already initialised – skipping")
            return

        logger.info(
            f"Initialising ChromaDB at: {settings.chroma_persist_dir}"
        )
        self._client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        logger.info(
            f"Loading HuggingFace embeddings ({settings.embedding_model}) …"
        )
        self._embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
        )
        logger.info("VectorStoreManager initialised successfully")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_initialised(self) -> None:
        if self._client is None or self._embeddings is None:
            raise RuntimeError(
                "VectorStoreManager is not initialised. "
                "Call initialize() first."
            )

    def _get_store(self, collection_name: str) -> Chroma:
        """
        Return a cached LangChain Chroma wrapper for *collection_name*,
        creating it lazily on first access.
        """
        self._ensure_initialised()
        if collection_name not in self._stores:
            self._stores[collection_name] = Chroma(
                client=self._client,
                collection_name=collection_name,
                embedding_function=self._embeddings,
            )
        return self._stores[collection_name]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_documents(
        self, documents: List[Document], collection_name: str
    ) -> None:
        """
        Add *documents* to the named ChromaDB collection.

        Documents are added in batches of 500 to avoid hitting ChromaDB's
        internal payload limits on large ingestion runs.
        """
        self._ensure_initialised()
        if not documents:
            logger.warning(
                f"add_documents called with empty list for '{collection_name}'"
            )
            return

        store = self._get_store(collection_name)

        # Sanitize metadata: ChromaDB requires scalar values only
        sanitized_docs = [
            Document(
                page_content=doc.page_content,
                metadata=_sanitize_metadata(doc.metadata),
            )
            for doc in documents
        ]

        batch_size = 500
        total = len(sanitized_docs)
        for start in range(0, total, batch_size):
            batch = sanitized_docs[start : start + batch_size]
            store.add_documents(batch)
            logger.debug(
                f"  [{collection_name}] added batch "
                f"{start + 1}–{min(start + batch_size, total)} / {total}"
            )

        logger.info(
            f"add_documents: {total} documents added to '{collection_name}'"
        )
        # Invalidate the cached store so the next access picks up the new
        # document count from ChromaDB.
        self._stores.pop(collection_name, None)

    def similarity_search(
        self, query: str, collection_name: str, k: int = 5
    ) -> List[Document]:
        """
        Perform a vector similarity search against *collection_name*.

        Returns up to *k* documents.  Returns an empty list when the
        collection does not exist yet or is empty.
        """
        self._ensure_initialised()
        try:
            store = self._get_store(collection_name)
            results = store.similarity_search(query, k=k)
            return results
        except Exception as exc:
            logger.warning(
                f"similarity_search failed for '{collection_name}': {exc}"
            )
            return []

    def get_stats(self) -> dict:
        """
        Return the document counts for both managed collections.

        Example return value::

            {"technical_docs_count": 412, "maintenance_history_count": 87}
        """
        self._ensure_initialised()

        def _count(name: str) -> int:
            try:
                col = self._client.get_collection(name)  # type: ignore[union-attr]
                return col.count()
            except Exception:
                # Collection does not exist yet
                return 0

        stats = {
            f"{_TECHNICAL_DOCS}_count": _count(_TECHNICAL_DOCS),
            f"{_MAINTENANCE_HISTORY}_count": _count(_MAINTENANCE_HISTORY),
        }
        logger.debug(f"get_stats: {stats}")
        return stats

    def is_populated(self, collection_name: str) -> bool:
        """
        Return ``True`` if *collection_name* contains at least one document.
        """
        self._ensure_initialised()
        try:
            col = self._client.get_collection(collection_name)  # type: ignore[union-attr]
            return col.count() > 0
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

vector_store = VectorStoreManager()
