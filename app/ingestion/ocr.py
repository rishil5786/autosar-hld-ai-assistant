"""
AUTOSAR HLD AI - OCR Module
Handles OCR processing for scanned PDFs.
Gracefully degrades when Tesseract is not installed.
"""

from typing import Optional, Tuple
from app.utils.logger import logger


_tesseract_available: Optional[bool] = None


def check_tesseract() -> bool:
    """Check if Tesseract OCR is available on the system."""
    global _tesseract_available
    if _tesseract_available is not None:
        return _tesseract_available

    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        _tesseract_available = True
        logger.info("Tesseract OCR is available.")
    except Exception:
        _tesseract_available = False
        logger.warning("Tesseract OCR is not available. OCR features will be disabled.")

    return _tesseract_available


def ocr_image(image, lang: str = "eng") -> str:
    """
    Perform OCR on a PIL Image.

    Args:
        image: PIL Image object
        lang: OCR language

    Returns:
        Extracted text or empty string
    """
    if not check_tesseract():
        return ""

    try:
        import pytesseract
        text = pytesseract.image_to_string(image, lang=lang)
        return text.strip()
    except Exception as e:
        logger.error(f"OCR processing failed: {e}")
        return ""


def ocr_pdf_page(page, dpi: int = 300) -> str:
    """
    OCR a PDF page by rendering it to an image first.

    Args:
        page: PyMuPDF page object
        dpi: Resolution for rendering

    Returns:
        OCR'd text
    """
    if not check_tesseract():
        return ""

    try:
        from PIL import Image
        import io

        pix = page.get_pixmap(dpi=dpi)
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))
        return ocr_image(image)
    except Exception as e:
        logger.error(f"PDF page OCR failed: {e}")
        return ""


def detect_scanned_page(page, min_text_length: int = 50) -> bool:
    """
    Detect if a PDF page is scanned (image-based) rather than text-based.

    Args:
        page: PyMuPDF page object
        min_text_length: Minimum text length to consider as text-based

    Returns:
        True if page appears to be scanned
    """
    text = page.get_text("text").strip()
    has_images = len(page.get_images()) > 0
    return len(text) < min_text_length and has_images
