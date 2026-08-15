import re
from typing import List, Optional, Tuple

from langchain.schema import Document
from rank_bm25 import BM25Okapi
from loguru import logger

from src.rag.vector_store import vector_store

# ---------------------------------------------------------------------------
# Tokenisation helper
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    """
    Tokenise *text* for BM25 indexing.

    Improvements over naive whitespace split:
    - Handles slash-delimited units: ``in/s`` → ``in s``
    - Strips leading/trailing punctuation (full-stops, hyphens) from tokens
    - Drops single-character tokens (noise) and empty strings
    """
    text = text.lower()
    # Split slash-delimited units (e.g. in/s → in s, NPSHa/NPSHr → NPSHa NPSHr)
    text = re.sub(r'([a-z])/([a-z])', r'\1 \2', text)
    # Split on whitespace and common delimiters
    tokens = re.split(r'[\s,;:()\[\]"\']+', text)
    # Strip leading/trailing punctuation (dots, hyphens, underscores)
    tokens = [re.sub(r'^[.\-_]+|[.\-_]+$', '', t) for t in tokens]
    # Remove empty strings and single-character tokens
    return [t for t in tokens if t and len(t) > 1]


# ---------------------------------------------------------------------------
# Cross-encoder reranking (lazy-loaded)
# ---------------------------------------------------------------------------

_cross_encoder = None


def _get_cross_encoder():
    """
    Lazy-load the cross-encoder model on first call.

    Returns the CrossEncoder instance, or ``None`` if unavailable.
    The result is cached globally after the first successful load.
    """
    global _cross_encoder
    if _cross_encoder is None:
        try:
            from sentence_transformers import CrossEncoder
            _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            logger.info("Cross-encoder loaded: cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception as e:
            logger.warning(f"Cross-encoder unavailable: {e}; falling back to RRF ranking")
            _cross_encoder = False  # sentinel: don't retry
    return _cross_encoder if _cross_encoder is not False else None


# ---------------------------------------------------------------------------
# HybridRetriever
# ---------------------------------------------------------------------------


class HybridRetriever:
    """
    Combines ChromaDB vector similarity search with BM25 keyword search via
    Reciprocal Rank Fusion (RRF).

    Fault-code boost: when the user query contains a fault code pattern
    (e.g. ``F001``, ``P013``, ``C005``), any retrieved document whose
    ``page_content`` contains that exact code is promoted to the top of the
    final result list.
    """

    # Fault-code regex: one letter from {F, P, C} (case-insensitive) + 3 digits
    _FAULT_CODE_RE = re.compile(r"\b([FCPfcp]\d{3})\b")

    def __init__(self) -> None:
        # Maps collection_name -> (BM25Okapi instance, list of Document objects)
        self._bm25_index: dict[str, Tuple[BM25Okapi, List[Document]]] = {}

    # ------------------------------------------------------------------
    # BM25 index management
    # ------------------------------------------------------------------

    def _get_bm25(
        self, collection_name: str
    ) -> Optional[Tuple[BM25Okapi, List[Document]]]:
        """
        Return the cached BM25 index for *collection_name*, building it on
        the first call.

        Returns ``None`` when the collection is empty or does not yet exist.
        """
        if collection_name in self._bm25_index:
            return self._bm25_index[collection_name]

        self._build_bm25_from_store(collection_name)
        return self._bm25_index.get(collection_name)

    def _build_bm25_from_store(self, collection_name: str) -> None:
        """
        Fetch **all** documents from *collection_name* via ChromaDB and build
        a BM25 index over their ``page_content``.

        The resulting ``(BM25Okapi, documents)`` tuple is cached in
        ``self._bm25_index``.
        """
        logger.debug(
            f"Building BM25 index for collection '{collection_name}' …"
        )
        try:
            # Retrieve a very large k to approximate "all documents".
            # ChromaDB's Python client doesn't expose a direct "get all"
            # method through LangChain, so we use a broad similarity query.
            # A neutral query with a very high k is the pragmatic approach.
            docs = vector_store.similarity_search(
                query="maintenance equipment fault", # broad query
                collection_name=collection_name,
                k=10_000,
            )
        except Exception as exc:
            logger.warning(
                f"Could not fetch documents for BM25 ({collection_name}): {exc}"
            )
            return

        if not docs:
            logger.debug(
                f"No documents found in '{collection_name}' – BM25 index not built"
            )
            return

        self._build_bm25(docs, collection_name)

    def _build_bm25(
        self, documents: List[Document], collection_name: str
    ) -> None:
        """
        Tokenise *documents* and construct a :class:`BM25Okapi` index, then
        cache it under *collection_name*.
        """
        corpus = [_tokenize(doc.page_content) for doc in documents]
        bm25 = BM25Okapi(corpus)
        self._bm25_index[collection_name] = (bm25, documents)
        logger.debug(
            f"BM25 index built for '{collection_name}' "
            f"({len(documents)} documents)"
        )

    # ------------------------------------------------------------------
    # Cross-encoder reranking
    # ------------------------------------------------------------------

    def _rerank_with_cross_encoder(
        self, query: str, candidates: List[Document], top_k: int
    ) -> List[Document]:
        """
        Rerank *candidates* using a cross-encoder that scores each
        (query, document) pair jointly for higher relevance accuracy.

        Falls back to returning ``candidates[:top_k]`` when the
        cross-encoder is unavailable or raises an exception.
        """
        ce = _get_cross_encoder()
        if ce is None or not candidates:
            return candidates[:top_k]
        try:
            pairs = [(query, doc.page_content) for doc in candidates]
            scores = ce.predict(pairs)
            scored = sorted(zip(scores, candidates), key=lambda t: t[0], reverse=True)
            logger.debug(
                f"Cross-encoder reranked {len(candidates)} candidates "
                f"→ returning top {top_k}"
            )
            return [doc for _, doc in scored[:top_k]]
        except Exception as e:
            logger.warning(f"Cross-encoder reranking failed: {e}; using RRF order")
            return candidates[:top_k]

    # ------------------------------------------------------------------
    # Reciprocal Rank Fusion
    # ------------------------------------------------------------------

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Document],
        bm25_results: List[Document],
        k: int = 60,
    ) -> List[Document]:
        """
        Merge two ranked document lists using Reciprocal Rank Fusion.

        Score formula: ``score(d) = sum over lists of 1 / (rank + k)``

        Documents are deduplicated by ``page_content``.  The merged list is
        returned sorted by descending RRF score.
        """
        # score_map : page_content -> (score, Document)
        score_map: dict[str, Tuple[float, Document]] = {}

        for rank, doc in enumerate(vector_results):
            key = doc.page_content
            prev_score, _ = score_map.get(key, (0.0, doc))
            score_map[key] = (prev_score + 1.0 / (rank + k), doc)

        for rank, doc in enumerate(bm25_results):
            key = doc.page_content
            prev_score, _ = score_map.get(key, (0.0, doc))
            score_map[key] = (prev_score + 1.0 / (rank + k), doc)

        sorted_items = sorted(
            score_map.values(), key=lambda t: t[0], reverse=True
        )
        return [doc for _, doc in sorted_items]

    # ------------------------------------------------------------------
    # Fault-code detection
    # ------------------------------------------------------------------

    def _detect_fault_code(self, query: str) -> Optional[str]:
        """
        Return the first fault-code pattern found in *query* (upper-cased),
        or ``None`` if no pattern is present.

        Pattern: one letter from ``{F, P, C}`` (case-insensitive) + 3 digits.
        Examples: ``F001``, ``p013``, ``C005``.
        """
        match = self._FAULT_CODE_RE.search(query)
        if match:
            return match.group(1).upper()
        return None

    # ------------------------------------------------------------------
    # Core retrieval
    # ------------------------------------------------------------------

    def retrieve(
        self, query: str, collection_name: str, k: int = 5
    ) -> List[Document]:
        """
        Retrieve the top-*k* most relevant documents for *query* from
        *collection_name* using hybrid vector + BM25 search with RRF merging.

        Algorithm
        ---------
        1. Vector search     : fetch ``k * 3`` candidates from ChromaDB.
        2. BM25 search       : score all indexed documents, take top ``k * 3``.
        3. RRF merge         : combine and re-rank both candidate lists.
        4. Fault-code boost  : if the query contains a fault code, move
                               documents mentioning that exact code to the front.
        5. Cross-encoder     : rerank the merged pool with a cross-encoder for
                               accurate relevance scoring.
        6. Return the top *k* documents.
        """
        candidates = k * 3

        # ---- 1. Vector search ----
        vector_results: List[Document] = []
        try:
            vector_results = vector_store.similarity_search(
                query=query,
                collection_name=collection_name,
                k=candidates,
            )
            logger.debug(
                f"Vector search returned {len(vector_results)} results "
                f"for collection '{collection_name}'"
            )
        except Exception as exc:
            logger.warning(f"Vector search failed: {exc}")

        # ---- 2. BM25 search ----
        bm25_results: List[Document] = []
        bm25_entry = self._get_bm25(collection_name)
        if bm25_entry is not None:
            bm25_obj, bm25_docs = bm25_entry
            query_tokens = _tokenize(query)
            scores = bm25_obj.get_scores(query_tokens)
            # Pair each document with its BM25 score, sort descending
            scored = sorted(
                zip(scores, bm25_docs), key=lambda t: t[0], reverse=True
            )
            bm25_results = [doc for _, doc in scored[:candidates]]
            logger.debug(
                f"BM25 search returned {len(bm25_results)} results "
                f"for collection '{collection_name}'"
            )
        else:
            logger.debug(
                f"No BM25 index available for '{collection_name}'; "
                "falling back to vector-only results"
            )

        # ---- 3. RRF merge ----
        merged = self._reciprocal_rank_fusion(vector_results, bm25_results)

        # ---- 4. Fault-code boost ----
        fault_code = self._detect_fault_code(query)
        if fault_code:
            logger.debug(f"Fault-code detected in query: {fault_code}; boosting matches")
            pattern = re.compile(re.escape(fault_code), re.IGNORECASE)
            boosted = [
                doc for doc in merged if pattern.search(doc.page_content)
            ]
            rest = [
                doc for doc in merged if not pattern.search(doc.page_content)
            ]
            merged = boosted + rest

        # ---- 5. Cross-encoder reranking ----
        result = self._rerank_with_cross_encoder(query, merged, top_k=k)

        logger.info(
            f"retrieve: returning {len(result)} documents "
            f"(collection='{collection_name}', query={query!r:.60s})"
        )
        return result

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def invalidate_cache(self) -> None:
        """Clear all cached BM25 indices (e.g. after new documents are added)."""
        self._bm25_index = {}
        logger.debug("BM25 cache invalidated")


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

retriever = HybridRetriever()
