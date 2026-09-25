"""
AUTOSAR HLD AI - RAG Retriever
Retrieves relevant document chunks using semantic search.
"""

from typing import List, Optional
from dataclasses import dataclass

from app.embeddings.embedding_service import get_embedding_service
from app.vectorstore.faiss_store import get_faiss_store, SearchResult
from app.utils.logger import logger


@dataclass
class RetrievalResult:
    """Retrieved context with metadata."""
    text: str
    document_name: str
    page_number: int
    section: str
    score: float
    chunk_id: str


def retrieve(
    query: str,
    top_k: int = 5,
    document_id: Optional[str] = None,
    min_score: float = 0.0
) -> List[RetrievalResult]:
    """
    Retrieve relevant chunks for a query.

    Args:
        query: User question
        top_k: Number of results
        document_id: Optional document filter
        min_score: Minimum relevance score

    Returns:
        List of RetrievalResult objects
    """
    embedding_service = get_embedding_service()
    faiss_store = get_faiss_store()

    if not embedding_service.is_available:
        if not embedding_service.initialize():
            logger.error("Embedding service unavailable for retrieval")
            return []

    if not faiss_store.is_available:
        if not faiss_store.initialize():
            logger.error("FAISS store unavailable for retrieval")
            return []

    # Generate query embedding
    query_embedding = embedding_service.embed_query(query)
    if query_embedding is None:
        logger.error("Failed to generate query embedding")
        return []

    # Search FAISS
    search_results = faiss_store.search(
        query_embedding=query_embedding,
        top_k=top_k,
        document_id=document_id
    )

    # Convert to RetrievalResult
    results = []
    for sr in search_results:
        if sr.score < min_score:
            continue
        results.append(RetrievalResult(
            text=sr.text,
            document_name=sr.metadata.get("document_name", "Unknown"),
            page_number=sr.metadata.get("page_number", 0),
            section=sr.metadata.get("section", "Unknown"),
            score=sr.score,
            chunk_id=sr.chunk_id
        ))

    logger.info(f"Retrieved {len(results)} chunks for query: {query[:50]}...")
    return results
