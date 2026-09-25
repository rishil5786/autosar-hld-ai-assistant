"""
AUTOSAR HLD AI - PDF Parser
Extracts text, headings, tables, and metadata from PDF documents.
Uses PyMuPDF (fitz) as the primary parser with pdfplumber fallback.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from app.utils.logger import logger


@dataclass
class PageContent:
    """Structured content from a single PDF page."""
    page_number: int
    text: str
    headings: List[str] = field(default_factory=list)
    tables: List[List[List[str]]] = field(default_factory=list)
    is_scanned: bool = False
    ocr_text: str = ""


@dataclass
class ParsedDocument:
    """Complete parsed document structure."""
    filename: str
    page_count: int
    pages: List[PageContent] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    ocr_used: bool = False
    total_text_length: int = 0


def parse_pdf(file_path: str, filename: str = "") -> ParsedDocument:
    """
    Parse a PDF document and extract all content.

    Args:
        file_path: Path to the PDF file
        filename: Original filename for reference

    Returns:
        ParsedDocument with all extracted content
    """
    import fitz  # PyMuPDF

    if not filename:
        filename = Path(file_path).name

    logger.info(f"Starting PDF parsing: {filename}")

    doc = fitz.open(file_path)
    parsed = ParsedDocument(
        filename=filename,
        page_count=len(doc),
        metadata=dict(doc.metadata) if doc.metadata else {}
    )

    total_text = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")

        # Detect if page might be scanned (very little text)
        is_scanned = len(text.strip()) < 50 and page.get_images()

        # Extract headings from text based on font analysis
        headings = _extract_headings_from_page(page)

        page_content = PageContent(
            page_number=page_num + 1,  # 1-indexed
            text=text,
            headings=headings,
            is_scanned=is_scanned
        )

        # Try to extract tables using pdfplumber
        try:
            tables = _extract_tables_pdfplumber(file_path, page_num)
            page_content.tables = tables
        except Exception as e:
            logger.debug(f"Table extraction failed on page {page_num + 1}: {e}")

        # If scanned, attempt OCR
        if is_scanned:
            ocr_text = _attempt_ocr(page)
            if ocr_text:
                page_content.ocr_text = ocr_text
                page_content.text = ocr_text
                parsed.ocr_used = True
                logger.info(f"OCR applied on page {page_num + 1}")

        total_text += len(page_content.text)
        parsed.pages.append(page_content)

    parsed.total_text_length = total_text
    doc.close()

    logger.info(
        f"PDF parsed: {filename}, {parsed.page_count} pages, "
        f"{total_text} chars, OCR: {parsed.ocr_used}"
    )
    return parsed


def _extract_headings_from_page(page) -> List[str]:
    """
    Extract headings by analyzing font sizes and styles.
    Headings typically have larger font sizes or bold text.
    """
    headings = []
    try:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    size = span["size"]
                    flags = span["flags"]

                    # Heuristic: larger fonts or bold text could be headings
                    is_bold = flags & 2 ** 4  # Bold flag
                    is_large = size >= 12

                    if text and (is_bold or is_large) and len(text) > 2 and len(text) < 200:
                        # Check for typical heading patterns
                        heading_pattern = re.compile(
                            r'^(\d+\.?\d*\.?\d*\.?\s|Chapter\s|Section\s|Appendix\s)',
                            re.IGNORECASE
                        )
                        if heading_pattern.match(text) or (is_large and is_bold):
                            if text not in headings:
                                headings.append(text)
    except Exception as e:
        logger.debug(f"Heading extraction error: {e}")

    return headings


def _extract_tables_pdfplumber(file_path: str, page_num: int) -> List[List[List[str]]]:
    """Extract tables from a PDF page using pdfplumber."""
    tables = []
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            if page_num < len(pdf.pages):
                page = pdf.pages[page_num]
                page_tables = page.extract_tables()
                if page_tables:
                    for table in page_tables:
                        cleaned = []
                        for row in table:
                            cleaned_row = [cell if cell else "" for cell in row]
                            cleaned.append(cleaned_row)
                        tables.append(cleaned)
    except ImportError:
        logger.debug("pdfplumber not available for table extraction")
    except Exception as e:
        logger.debug(f"pdfplumber table extraction error: {e}")

    return tables


def _attempt_ocr(page) -> str:
    """
    Attempt OCR on a page image.
    Gracefully handles missing Tesseract.
    """
    try:
        import pytesseract
        from PIL import Image
        import io

        # Render page to image
        pix = page.get_pixmap(dpi=300)
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))

        # Run OCR
        text = pytesseract.image_to_string(image)
        return text.strip()
    except ImportError:
        logger.warning("pytesseract not installed. OCR unavailable.")
        return ""
    except Exception as e:
        logger.warning(f"OCR failed: {e}. Tesseract may not be installed.")
        return ""


def validate_pdf(file_path: str, file_size: int = 0) -> Tuple[bool, str]:
    """
    Validate a PDF file.

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        import fitz
        doc = fitz.open(file_path)

        if doc.page_count == 0:
            doc.close()
            return False, "PDF has no pages."

        # Try to read first page
        first_page = doc[0]
        _ = first_page.get_text()

        doc.close()
        return True, ""
    except Exception as e:
        return False, f"Invalid or corrupted PDF: {str(e)}"
