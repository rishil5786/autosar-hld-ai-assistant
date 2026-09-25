"""
AUTOSAR HLD AI - RAG Pipeline
End-to-end Retrieval-Augmented Generation pipeline.
"""

from typing import Optional, List
from app.rag.retriever import retrieve, RetrievalResult
from app.rag.prompt_builder import build_rag_prompt
from app.rag.llm_service import get_llm_service
from app.rag.citation import generate_citations, format_citations_text, assess_groundedness
from app.backend.schemas import QueryResponse, Citation, ChunkResponse
from app.utils.logger import logger


def run_rag_query(
    question: str,
    document_id: Optional[str] = None,
    top_k: int = 5
) -> QueryResponse:
    """
    Execute the full RAG pipeline:
    1. Embed the question
    2. Retrieve relevant chunks from FAISS
    3. Build prompt with context
    4. Generate answer with LLM (or show retrieval-only)
    5. Generate citations
    6. Assess groundedness

    Args:
        question: User's question
        document_id: Optional document filter
        top_k: Number of chunks to retrieve

    Returns:
        QueryResponse with answer, citations, and metadata
    """
    logger.info(f"RAG query: {question[:80]}...")

    # Step 1-2: Retrieve relevant chunks
    retrieval_results = retrieve(
        query=question,
        top_k=top_k,
        document_id=document_id
    )

    if not retrieval_results:
        return QueryResponse(
            answer="No relevant document content was found. Please upload an AUTOSAR HLD document first.",
            citations=[],
            llm_available=False,
            groundedness="ungrounded",
            retrieved_chunks=[]
        )

    # Step 3: Build prompt
    prompt = build_rag_prompt(question, retrieval_results)

    # Step 4: Generate answer
    llm_service = get_llm_service()
    llm_available = llm_service.is_available

    if llm_available:
        answer = llm_service.generate(prompt)
        if answer is None:
            llm_available = False
            answer = _build_retrieval_only_answer(question, retrieval_results)
    else:
        answer = _build_retrieval_only_answer(question, retrieval_results)

    # Step 5: Generate citations
    citations = generate_citations(retrieval_results)

    # Step 6: Assess groundedness
    groundedness = assess_groundedness(answer, citations)

    # Build retrieved chunks for display
    retrieved_chunks = [
        ChunkResponse(
            chunk_id=r.chunk_id,
            document_name=r.document_name,
            page_number=r.page_number,
            section=r.section,
            text=r.text
        )
        for r in retrieval_results
    ]

    return QueryResponse(
        answer=answer,
        citations=citations,
        llm_available=llm_available,
        groundedness=groundedness,
        retrieved_chunks=retrieved_chunks
    )


def _build_retrieval_only_answer(
    question: str,
    results: List[RetrievalResult]
) -> str:
    """
    Build a retrieval-only response when no LLM is available.
    Shows the retrieved evidence directly.
    """
    lines = [
        "**⚠️ LLM unavailable — showing retrieved evidence only.**\n",
        f"**Your question:** {question}\n",
        "**Retrieved evidence from the document:**\n"
    ]

    for i, result in enumerate(results, 1):
        lines.append(
            f"**[{i}]** _{result.document_name} — Page {result.page_number} — "
            f"{result.section}_ (Score: {result.score:.3f})\n"
        )
        # Show first 400 chars of each chunk
        text = result.text[:400] + "..." if len(result.text) > 400 else result.text
        lines.append(f"> {text}\n")

    lines.append(
        "\n*To get AI-generated answers, configure an LLM provider in the Settings page.*"
    )
    return "\n".join(lines)
