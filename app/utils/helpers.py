"""
AUTOSAR HLD AI - Helper Utilities
Common utility functions used across the application.
"""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Optional


def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())


def generate_document_id(filename: str, content_hash: str) -> str:
    """Generate a deterministic document ID from filename and content."""
    return hashlib.sha256(f"{filename}:{content_hash}".encode()).hexdigest()[:16]


def compute_file_hash(content: bytes) -> str:
    """Compute SHA-256 hash of file content."""
    return hashlib.sha256(content).hexdigest()


def now_utc() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to max_length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def clean_text(text: str) -> str:
    """Clean extracted text by normalizing whitespace and removing artifacts."""
    import re
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove null bytes
    text = text.replace('\x00', '')
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def safe_json_serialize(obj: Any) -> Any:
    """Make objects JSON-serializable."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, bytes):
        return obj.decode('utf-8', errors='replace')
    return str(obj)
