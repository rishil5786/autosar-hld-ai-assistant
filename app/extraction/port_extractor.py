"""
AUTOSAR HLD AI - Port Extractor
Extracts port definitions from HLD documents.
"""

import re
from typing import List, Dict
from app.utils.logger import logger


def extract_ports(text: str, page_number: int = 0, section: str = "") -> List[Dict]:
    """
    Extract AUTOSAR ports from document text.

    Args:
        text: Document text
        page_number: Source page
        section: Source section

    Returns:
        List of port dictionaries
    """
    ports = []
    seen = set()

    patterns = [
        # P_Xxx (Provided ports)
        (r'\b(P_[A-Z][a-zA-Z_]+)\b', 'provided'),
        # R_Xxx (Required ports)
        (r'\b(R_[A-Z][a-zA-Z_]+)\b', 'required'),
        # PPort, RPort references
        (r'\b(PPort_[A-Z][a-zA-Z_]+)\b', 'provided'),
        (r'\b(RPort_[A-Z][a-zA-Z_]+)\b', 'required'),
        # Explicit port references
        (r'(?:provided?|pport)\s+port\s*[:\-–]\s*([A-Z][a-zA-Z_]+)', 'provided'),
        (r'(?:required?|rport)\s+port\s*[:\-–]\s*([A-Z][a-zA-Z_]+)', 'required'),
        # Generic port patterns
        (r'\b([A-Z][a-zA-Z]*Port)\b', 'unknown'),
    ]

    for pattern, port_type in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            name = match.strip()
            if name and name not in seen and len(name) > 2:
                component = _find_port_component(text, name)
                interface = _find_port_interface(text, name)
                ports.append({
                    "name": name,
                    "port_type": port_type,
                    "direction": "out" if port_type == "provided" else "in" if port_type == "required" else "",
                    "interface_name": interface,
                    "component_name": component,
                    "source_page": page_number,
                    "confidence": 0.7 if port_type != 'unknown' else 0.5,
                })
                seen.add(name)

    logger.debug(f"Extracted {len(ports)} ports from page {page_number}")
    return ports


def _find_port_component(text: str, port_name: str) -> str:
    """Find which component owns this port."""
    patterns = [
        rf'([A-Z][a-zA-Z]+(?:Manager|Control|Handler|Service))\s*[:\.\-]\s*.*{re.escape(port_name)}',
        rf'{re.escape(port_name)}\s+(?:of|in|on)\s+([A-Z][a-zA-Z]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def _find_port_interface(text: str, port_name: str) -> str:
    """Find interface associated with this port."""
    patterns = [
        rf'{re.escape(port_name)}\s*[:\-–]?\s*([A-Z][a-zA-Z]*Interface)',
        rf'{re.escape(port_name)}\s*\(([A-Z][a-zA-Z_]+)\)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""
