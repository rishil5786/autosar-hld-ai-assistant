"""
AUTOSAR HLD AI - Interface Extractor
Extracts interfaces from HLD documents.
"""

import re
from typing import List, Dict
from app.utils.logger import logger


def extract_interfaces(text: str, page_number: int = 0, section: str = "") -> List[Dict]:
    """
    Extract AUTOSAR interfaces from document text.

    Args:
        text: Document text
        page_number: Source page
        section: Source section

    Returns:
        List of interface dictionaries
    """
    interfaces = []
    seen_names = set()

    patterns = [
        # Standard AUTOSAR If_Xxx naming
        r'\b(If_[A-Za-z0-9_]+)\b',
        r'\b(I_[A-Za-z0-9_]+)\b',
        # XxxInterface, XxxIf
        r'\b([A-Z][a-zA-Z]*Interface)\b',
        r'\b([A-Z][a-zA-Z]*_Interface)\b',
        r'\b([A-Z][a-zA-Z]*If)\b',
        # Sender-Receiver, Client-Server patterns
        r'\b(SR_[A-Z][a-zA-Z_]+)\b',
        r'\b(CS_[A-Z][a-zA-Z_]+)\b',
        # Explicit interface references
        r'interface\s*[:\-–]\s*([A-Za-z0-9_]+)',
        r'(?:provides?|requires?)\s+(?:the\s+)?interface\s+([A-Za-z0-9_]+)',
        # Bullet list under interfaces section
        r'(?:^|\n)\s*[-•●*]\s*(If_[A-Za-z0-9_]+|I_[A-Za-z0-9_]+|[A-Z][a-zA-Z0-9_]+Interface)\s*[:\-–]',
        # Interface in descriptions
        r'(?:data|service|communication)\s+interface\s+([A-Za-z0-9_]+)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            name = match.strip() if isinstance(match, str) else match[0].strip()
            if name and name not in seen_names and len(name) > 2 and len(name) < 80:
                if name.lower() not in {"interface", "interfaces", "standard"}:
                    interface_type = _classify_interface(name, text)
                    related = _find_related_component(text, name)
                    interfaces.append({
                        "name": name,
                        "interface_type": interface_type,
                        "description": _extract_if_description(text, name),
                        "source_page": page_number,
                        "source_section": section,
                        "related_component": related,
                        "confidence": 0.85 if ('if_' in name.lower() or 'interface' in name.lower()) else 0.6,
                    })
                    seen_names.add(name)

    logger.debug(f"Extracted {len(interfaces)} interfaces from page {page_number}")
    return interfaces


def _classify_interface(name: str, context: str) -> str:
    """Classify interface type."""
    name_lower = name.lower()
    if 'sr_' in name_lower or 'sender' in context.lower():
        return 'Sender-Receiver'
    elif 'cs_' in name_lower or 'client' in context.lower() or 'command' in name_lower:
        return 'Client-Server'
    elif 'data' in name_lower or 'voltage' in name_lower or 'temp' in name_lower:
        return 'Sender-Receiver'
    elif 'service' in name_lower:
        return 'Service'
    elif 'status' in name_lower:
        return 'Sender-Receiver'
    return 'Sender-Receiver'


def _extract_if_description(text: str, name: str) -> str:
    """Extract interface description."""
    pattern = re.compile(rf'{re.escape(name)}\s*[:\-–]?\s*(.{{10,150}}?)(?:\n|\.|$)', re.DOTALL)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _find_related_component(text: str, interface_name: str) -> str:
    """Find component related to this interface."""
    patterns = [
        rf'([A-Z][a-zA-Z]+(?:Manager|Control|Handler|Service|Monitor|Estimator))\s+(?:provides?|uses?|requires?)\s+{re.escape(interface_name)}',
        rf'{re.escape(interface_name)}\s+(?:of|from|in|Related Component:\s*)\s*([A-Z][a-zA-Z]+(?:Manager|Control|Handler|Service|Monitor|Estimator))',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""
