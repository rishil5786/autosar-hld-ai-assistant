"""
AUTOSAR HLD AI - Metadata Extractor
Extracts and manages document metadata.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from app.utils.logger import logger
from app.utils.helpers import compute_file_hash, generate_document_id


def extract_metadata(file_path: str, filename: str, file_content: bytes) -> Dict[str, Any]:
    """
    Extract metadata from a PDF file.

    Args:
        file_path: Path to the PDF
        filename: Original filename
        file_content: Raw file bytes

    Returns:
        Metadata dictionary
    """
    import fitz

    file_hash = compute_file_hash(file_content)
    doc_id = generate_document_id(filename, file_hash)

    metadata = {
        "document_id": doc_id,
        "filename": filename,
        "file_hash": file_hash,
        "file_size": len(file_content),
        "extraction_date": datetime.now().isoformat()
    }

    try:
        doc = fitz.open(file_path)
        pdf_meta = doc.metadata
        metadata.update({
            "page_count": len(doc),
            "title": pdf_meta.get("title", ""),
            "author": pdf_meta.get("author", ""),
            "subject": pdf_meta.get("subject", ""),
            "creator": pdf_meta.get("creator", ""),
            "producer": pdf_meta.get("producer", ""),
            "creation_date": pdf_meta.get("creationDate", ""),
            "modification_date": pdf_meta.get("modDate", ""),
        })
        doc.close()
    except Exception as e:
        logger.error(f"Metadata extraction error: {e}")

    return metadata


def detect_version_from_filename(filename: str) -> Optional[str]:
    """
    Try to detect document version from filename.

    Examples:
        HLD_V1.pdf -> V1
        AUTOSAR_HLD_v2.3.pdf -> v2.3
        document_rev3.pdf -> rev3
    """
    import re
    patterns = [
        r'[vV](\d+\.?\d*)',     # V1, v2.3
        r'[rR]ev(\d+\.?\d*)',   # rev3, Rev2.1
        r'[vV]ersion[\s_]?(\d+\.?\d*)',  # version1, Version_2
    ]
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            return match.group(0)
    return None
