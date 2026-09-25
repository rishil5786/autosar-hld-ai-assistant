"""
AUTOSAR HLD AI - Component Extractor
Extracts software components from HLD documents using rule-based + NLP.
"""

import re
from typing import List, Dict, Optional
from app.utils.logger import logger


def extract_components(text: str, page_number: int = 0, section: str = "") -> List[Dict]:
    """
    Extract AUTOSAR software components from document text.

    Uses multiple strategies:
    1. Pattern matching for common AUTOSAR naming conventions
    2. Section heading analysis
    3. Contextual keyword matching

    Args:
        text: Document text to analyze
        page_number: Source page number
        section: Source section name

    Returns:
        List of extracted component dictionaries
    """
    components = []
    seen_names = set()

    # Strategy 1: CamelCase/PascalCase component names with keywords
    component_patterns = [
        # "XxxManager", "XxxControl", "XxxHandler" etc.
        r'\b([A-Z][a-zA-Z]*(?:Manager|Control|Controller|Handler|Service|Gateway|Monitor|Driver|Interface|Module|Server|Client|Proxy|Adapter|Wrapper|Sensor|Actuator|Diagnostic|Communication))\b',
        # Explicit "component" references
        r'(?:software\s+)?component[s]?\s*[:\-–]\s*([A-Z][a-zA-Z]+(?:\s*,\s*[A-Z][a-zA-Z]+)*)',
        # SWC references
        r'\bSWC[_\s]*([A-Z][a-zA-Z_]+)\b',
        # Component names in lists/bullets
        r'(?:^|\n)\s*[-•●]\s*([A-Z][a-zA-Z]{2,}(?:Manager|Control|Handler|Service|Gateway|Module))\b',
    ]

    for pattern in component_patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            # Handle comma-separated names
            names = [n.strip() for n in match.split(',')] if ',' in match else [match.strip()]
            for name in names:
                name = name.strip()
                if name and name not in seen_names and len(name) > 2 and len(name) < 60:
                    # Filter out common false positives
                    if name.lower() not in _false_positive_set():
                        components.append({
                            "name": name,
                            "description": _extract_description(text, name),
                            "component_type": _classify_component(name),
                            "source_page": page_number,
                            "source_section": section,
                            "confidence": _calculate_confidence(text, name),
                        })
                        seen_names.add(name)

    # Strategy 2: Look for component definitions in structured sections
    definition_patterns = [
        r'(?:Component|Module|SWC)\s*Name\s*[:\-–]\s*([A-Z][a-zA-Z_]+)',
        r'(?:##?\s*)?(\d+\.?\d*\.?\d*\.?\s+)?([A-Z][a-zA-Z]+(?:Manager|Control|Handler|Service))\s*\n',
    ]
    for pattern in definition_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            name = match[-1] if isinstance(match, tuple) else match
            name = name.strip()
            if name and name not in seen_names and len(name) > 2:
                if name.lower() not in _false_positive_set():
                    components.append({
                        "name": name,
                        "description": _extract_description(text, name),
                        "component_type": _classify_component(name),
                        "source_page": page_number,
                        "source_section": section,
                        "confidence": 0.7,
                    })
                    seen_names.add(name)

    logger.debug(f"Extracted {len(components)} components from page {page_number}")
    return components


def _extract_description(text: str, component_name: str) -> str:
    """Extract a description for a component from surrounding text."""
    # Find the component name and grab text after it
    pattern = re.compile(
        rf'{re.escape(component_name)}\s*[:\-–]?\s*(.{{10,200}}?)(?:\n\n|\.|$)',
        re.DOTALL
    )
    match = pattern.search(text)
    if match:
        desc = match.group(1).strip()
        # Clean up
        desc = re.sub(r'\s+', ' ', desc)
        return desc
    return ""


def _classify_component(name: str) -> str:
    """Classify component type based on naming convention."""
    name_lower = name.lower()
    if 'manager' in name_lower:
        return 'Manager'
    elif 'control' in name_lower:
        return 'Controller'
    elif 'handler' in name_lower:
        return 'Handler'
    elif 'service' in name_lower:
        return 'Service'
    elif 'gateway' in name_lower:
        return 'Gateway'
    elif 'driver' in name_lower:
        return 'Driver'
    elif 'sensor' in name_lower:
        return 'Sensor'
    elif 'diagnostic' in name_lower:
        return 'Diagnostic'
    elif 'monitor' in name_lower:
        return 'Monitor'
    return 'Component'


def _calculate_confidence(text: str, name: str) -> float:
    """Calculate extraction confidence based on context."""
    confidence = 0.5
    # Higher confidence if mentioned multiple times
    count = text.lower().count(name.lower())
    if count >= 3:
        confidence += 0.3
    elif count >= 2:
        confidence += 0.2

    # Higher confidence if near keywords
    context_keywords = ['component', 'module', 'swc', 'software', 'architecture']
    for kw in context_keywords:
        if kw in text.lower():
            confidence += 0.05
    return min(confidence, 1.0)


def _false_positive_set() -> set:
    """Common words that look like components but aren't."""
    return {
        'abstract', 'introduction', 'overview', 'architecture', 'document',
        'appendix', 'reference', 'standard', 'specification', 'interface',
        'description', 'implementation', 'configuration', 'requirements',
        'deployment', 'analysis', 'design', 'testing', 'validation',
        'datatype', 'revision', 'version', 'section', 'chapter', 'figure',
        'table', 'summary', 'conclusion', 'bibliography',
    }
