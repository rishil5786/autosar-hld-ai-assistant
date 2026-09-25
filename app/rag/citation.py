"""
AUTOSAR HLD AI - Citation Generator
Creates structured citations from retrieval results.
"""

from typing import List, Dict
from app.rag.retriever import RetrievalResult
from app.backend.schemas import Citation


def generate_citations(retrieval_results: List[RetrievalResult]) -> List[Citation]:
    """
    Generate structured citations from retrieval results.

    Args:
        retrieval_results: List of retrieved chunks

    Returns:
        List of Citation objects
    """
    citations = []
    seen = set()

    for result in retrieval_results:
        # Create a unique key to avoid duplicate citations
        key = f"{result.document_name}:{result.page_number}:{result.section}"
        if key in seen:
            continue
        seen.add(key)

        citation = Citation(
            document_name=result.document_name,
            page_number=result.page_number,
            section=result.section or "Unknown Section",
            text_excerpt=result.text[:200] + "..." if len(result.text) > 200 else result.text,
            relevance_score=round(result.score, 4)
        )
        citations.append(citation)

    return citations


def format_citations_text(citations: List[Citation]) -> str:
    """Format citations as readable text for display."""
    if not citations:
        return "No sources available."

    lines = ["**Sources:**"]
    for i, c in enumerate(citations, 1):
        lines.append(
            f"{i}. {c.document_name} — Page {c.page_number} — {c.section} "
            f"(relevance: {c.relevance_score:.2f})"
        )
    return "\n".join(lines)


def assess_groundedness(answer: str, citations: List[Citation]) -> str:
    """
    Assess how well the answer is grounded in sources.

    Returns: "grounded", "partial", or "ungrounded"
    """
    if not citations:
        return "ungrounded"

    # Check if the answer acknowledges lack of evidence
    no_evidence_phrases = [
        "could not find sufficient evidence",
        "not enough information",
        "no relevant context",
        "cannot determine"
    ]
    for phrase in no_evidence_phrases:
        if phrase.lower() in answer.lower():
            return "grounded"  # Honest answer is grounded

    # Check if answer references sources
    has_source_ref = any(
        c.document_name.lower() in answer.lower() or
        f"page {c.page_number}" in answer.lower()
        for c in citations
    )

    avg_score = sum(c.relevance_score for c in citations) / len(citations)

    if has_source_ref and avg_score > 0.5:
        return "grounded"
    elif avg_score > 0.3:
        return "partial"
    else:
        return "ungrounded"
