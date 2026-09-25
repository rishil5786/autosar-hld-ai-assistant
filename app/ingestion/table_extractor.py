"""
AUTOSAR HLD AI - Table Extractor
Specialized extraction of tables from PDF documents.
"""

import re
from typing import List, Dict, Optional
from app.utils.logger import logger


def extract_tables_from_text(text: str) -> List[Dict]:
    """
    Extract table-like structures from plain text.
    Useful when pdfplumber fails or for OCR'd text.

    Args:
        text: Plain text content

    Returns:
        List of detected table structures
    """
    tables = []
    lines = text.split('\n')
    current_table = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_table and len(current_table) >= 2:
                tables.append(_parse_text_table(current_table))
                current_table = []
                in_table = False
            continue

        # Detect table-like lines (contain multiple tab/pipe separators)
        separators = stripped.count('\t') + stripped.count('|') + stripped.count('  ')
        if separators >= 2 or re.match(r'^[-|+]+$', stripped):
            in_table = True
            if not re.match(r'^[-|+]+$', stripped):  # Skip separator lines
                current_table.append(stripped)
        elif in_table:
            current_table.append(stripped)

    if in_table and len(current_table) >= 2:
        tables.append(_parse_text_table(current_table))

    return tables


def _parse_text_table(rows: List[str]) -> Dict:
    """Parse text rows into a structured table."""
    parsed_rows = []
    for row in rows:
        # Split by tabs, pipes, or multiple spaces
        if '|' in row:
            cells = [c.strip() for c in row.split('|') if c.strip()]
        elif '\t' in row:
            cells = [c.strip() for c in row.split('\t') if c.strip()]
        else:
            cells = re.split(r'\s{2,}', row.strip())
        parsed_rows.append(cells)

    return {
        "headers": parsed_rows[0] if parsed_rows else [],
        "rows": parsed_rows[1:] if len(parsed_rows) > 1 else [],
        "raw_rows": rows
    }


def format_table_as_text(table: Dict) -> str:
    """Format a parsed table back into readable text for chunking."""
    lines = []
    if table.get("headers"):
        lines.append(" | ".join(table["headers"]))
        lines.append("-" * len(lines[0]))
    for row in table.get("rows", []):
        lines.append(" | ".join(row))
    return "\n".join(lines)
