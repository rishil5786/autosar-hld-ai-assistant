"""
AUTOSAR HLD AI - Context-Aware Chunker
Splits documents into meaningful, metadata-preserving chunks.
Uses section-aware and heading-aware splitting, NOT blind character splits.
"""

import re
import hashlib
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from app.ingestion.pdf_parser import ParsedDocument, PageContent
from app.utils.logger import logger


@dataclass
class DocumentChunk:
    """A single chunk with full metadata."""
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    section: str
    text: str
    chunk_index: int
    token_count: int = 0
    metadata: Dict = field(default_factory=dict)


def chunk_document(
    parsed_doc: ParsedDocument,
    document_id: str,
    max_chunk_size: int = 800,
    overlap: int = 100,
    min_chunk_size: int = 50
) -> List[DocumentChunk]:
    """
    Split a parsed document into context-aware chunks.

    Strategy:
    1. Process page by page
    2. Identify section boundaries via headings
    3. Split within sections at paragraph boundaries
    4. Add overlap for context continuity
    5. Preserve all metadata

    Args:
        parsed_doc: ParsedDocument from the parser
        document_id: Unique document identifier
        max_chunk_size: Maximum characters per chunk
        overlap: Character overlap between consecutive chunks
        min_chunk_size: Minimum chunk size to keep

    Returns:
        List of DocumentChunk objects
    """
    logger.info(f"Chunking document: {parsed_doc.filename} ({parsed_doc.page_count} pages)")

    chunks: List[DocumentChunk] = []
    chunk_index = 0
    current_section = "Document Start"

    for page in parsed_doc.pages:
        page_text = page.text.strip()
        if not page_text:
            continue

        # Update current section from headings on this page
        if page.headings:
            current_section = page.headings[0]

        # Split page text into paragraphs/sections
        segments = _split_into_segments(page_text, page.headings)

        for segment_text, segment_section in segments:
            if segment_section:
                current_section = segment_section

            if len(segment_text.strip()) < min_chunk_size:
                continue

            # If segment fits in one chunk, create it directly
            if len(segment_text) <= max_chunk_size:
                chunk = _create_chunk(
                    text=segment_text.strip(),
                    document_id=document_id,
                    document_name=parsed_doc.filename,
                    page_number=page.page_number,
                    section=current_section,
                    chunk_index=chunk_index
                )
                chunks.append(chunk)
                chunk_index += 1
            else:
                # Split large segments with overlap
                sub_chunks = _split_with_overlap(
                    segment_text, max_chunk_size, overlap
                )
                for sub_text in sub_chunks:
                    if len(sub_text.strip()) < min_chunk_size:
                        continue
                    chunk = _create_chunk(
                        text=sub_text.strip(),
                        document_id=document_id,
                        document_name=parsed_doc.filename,
                        page_number=page.page_number,
                        section=current_section,
                        chunk_index=chunk_index
                    )
                    chunks.append(chunk)
                    chunk_index += 1

        # Add table content as separate chunks
        for table in page.tables:
            table_text = _format_table(table)
            if len(table_text.strip()) >= min_chunk_size:
                chunk = _create_chunk(
                    text=f"[Table on Page {page.page_number}]\n{table_text}",
                    document_id=document_id,
                    document_name=parsed_doc.filename,
                    page_number=page.page_number,
                    section=current_section,
                    chunk_index=chunk_index,
                    extra_metadata={"is_table": True}
                )
                chunks.append(chunk)
                chunk_index += 1

    logger.info(f"Created {len(chunks)} chunks from {parsed_doc.filename}")
    return chunks


def _split_into_segments(text: str, headings: List[str]) -> List[tuple]:
    """
    Split text into segments based on headings and paragraph boundaries.

    Returns list of (text, section_name) tuples.
    """
    if not headings:
        # Split by double newlines (paragraphs) if no headings
        paragraphs = re.split(r'\n\s*\n', text)
        return [(p, None) for p in paragraphs if p.strip()]

    segments = []
    remaining = text
    current_section = None

    # Sort headings by their position in text
    heading_positions = []
    for heading in headings:
        pos = remaining.find(heading)
        if pos >= 0:
            heading_positions.append((pos, heading))

    heading_positions.sort(key=lambda x: x[0])

    if not heading_positions:
        return [(text, None)]

    # Extract text before first heading
    first_pos = heading_positions[0][0]
    if first_pos > 0:
        segments.append((remaining[:first_pos], None))

    # Extract text between headings
    for i, (pos, heading) in enumerate(heading_positions):
        if i + 1 < len(heading_positions):
            next_pos = heading_positions[i + 1][0]
            segment_text = remaining[pos:next_pos]
        else:
            segment_text = remaining[pos:]
        segments.append((segment_text, heading))

    return segments


def _split_with_overlap(text: str, max_size: int, overlap: int) -> List[str]:
    """Split text into overlapping chunks at sentence boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_size:
            current += (" " + sentence if current else sentence)
        else:
            if current:
                chunks.append(current)
            # Start new chunk with overlap from the end of the previous
            if overlap > 0 and current:
                overlap_text = current[-overlap:] if len(current) > overlap else current
                current = overlap_text + " " + sentence
            else:
                current = sentence

    if current:
        chunks.append(current)

    return chunks


def _create_chunk(
    text: str,
    document_id: str,
    document_name: str,
    page_number: int,
    section: str,
    chunk_index: int,
    extra_metadata: Dict = None
) -> DocumentChunk:
    """Create a DocumentChunk with a deterministic ID."""
    chunk_id = hashlib.md5(
        f"{document_id}:{page_number}:{chunk_index}:{text[:50]}".encode()
    ).hexdigest()[:16]

    metadata = {
        "document_id": document_id,
        "document_name": document_name,
        "page_number": page_number,
        "section": section,
    }
    if extra_metadata:
        metadata.update(extra_metadata)

    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        document_name=document_name,
        page_number=page_number,
        section=section,
        text=text,
        chunk_index=chunk_index,
        token_count=len(text.split()),
        metadata=metadata
    )


def _format_table(table: List[List[str]]) -> str:
    """Format a table as readable text."""
    lines = []
    for row in table:
        lines.append(" | ".join(str(cell) for cell in row))
    return "\n".join(lines)
