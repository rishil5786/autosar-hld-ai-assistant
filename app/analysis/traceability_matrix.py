"""
AUTOSAR HLD AI - Traceability Matrix Generator
Generates bidirectional traceability matrices linking Functional Requirements,
Software Components, Ports, Interfaces, and Runnables.
"""

from typing import List, Dict, Any, Optional
import re
from app.utils.logger import logger


class TraceabilityEngine:
    """
    Builds traceability matrices and coverage analytics for AUTOSAR HLD documents.
    """

    def __init__(self):
        pass

    def extract_requirements(self, text_or_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract requirements statements and IDs (e.g., REQ_BMS_001, SYS_REQ_042) from text chunks.
        """
        requirements = []
        seen_ids = set()

        req_pattern = re.compile(
            r'\b((?:REQ|SYS_REQ|SW_REQ|SWR|AUTOSAR_REQ|FSR|TSR|HLD_REQ)[_-][A-Za-z0-9_-]+)\b\s*[:\-–]?\s*([^\n\r]+)',
            re.IGNORECASE
        )

        for chunk in text_or_chunks:
            text = chunk.get("text", "")
            page = chunk.get("page_number", 0)
            section = chunk.get("section", "")

            matches = req_pattern.findall(text)
            for req_id, req_desc in matches:
                req_id_clean = req_id.strip()
                if req_id_clean not in seen_ids:
                    seen_ids.add(req_id_clean)
                    requirements.append({
                        "id": req_id_clean,
                        "description": req_desc.strip(),
                        "source_page": page,
                        "source_section": section
                    })

        # If few or no requirements found via strict ID format, extract bullet points mentioning 'shall' or 'must'
        if len(requirements) < 3:
            shall_pattern = re.compile(
                r'(?:^|\n)\s*[-•●*]\s*([A-Z][^\n\r]*(?:shall|must|is required to|shall provide)[^\n\r]+)',
                re.IGNORECASE
            )
            idx = len(requirements) + 1
            for chunk in text_or_chunks:
                text = chunk.get("text", "")
                page = chunk.get("page_number", 0)
                matches = shall_pattern.findall(text)
                for req_stmt in matches:
                    if len(req_stmt) > 20:
                        req_id = f"HLD_REQ_{idx:03d}"
                        requirements.append({
                            "id": req_id,
                            "description": req_stmt.strip(),
                            "source_page": page,
                            "source_section": chunk.get("section", "")
                        })
                        idx += 1

        return requirements

    def build_traceability_matrix(
        self,
        requirements: List[Dict[str, Any]],
        components: List[Dict[str, Any]],
        interfaces: List[Dict[str, Any]],
        ports: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Map requirements to components, ports, and interfaces based on semantic overlap.
        """
        logger.info(f"Building traceability matrix for {len(requirements)} requirements and {len(components)} SWCs")

        matrix_rows = []
        covered_reqs = set()
        covered_components = set()

        for req in requirements:
            req_text = f"{req.get('id', '')} {req.get('description', '')}".lower()
            mapped_swcs = []
            mapped_interfaces = []
            mapped_ports = []

            for comp in components:
                c_name = comp.get("name", "")
                # Check keyword match
                if c_name.lower() in req_text or any(token.lower() in req_text for token in re.findall(r'[A-Z][a-z]+', c_name) if len(token) > 3):
                    mapped_swcs.append(c_name)
                    covered_components.add(c_name)

            for iface in interfaces:
                i_name = iface.get("name", "")
                if i_name.lower() in req_text:
                    mapped_interfaces.append(i_name)

            for p in ports:
                p_name = p.get("name", "")
                if p_name.lower() in req_text or (p.get("component_name") in mapped_swcs):
                    if len(mapped_ports) < 3:
                        mapped_ports.append(f"{p.get('component_name', '')}::{p_name}")

            # If no direct match found, assign to closest matching SWC or general architecture
            status = "Mapped" if mapped_swcs else "Unmapped"
            if mapped_swcs:
                covered_reqs.add(req.get("id"))

            matrix_rows.append({
                "requirement_id": req.get("id"),
                "requirement_desc": req.get("description"),
                "source_page": req.get("source_page"),
                "status": status,
                "components": mapped_swcs,
                "interfaces": mapped_interfaces,
                "ports": mapped_ports
            })

        total_reqs = len(requirements)
        req_coverage_pct = round((len(covered_reqs) / total_reqs * 100), 1) if total_reqs > 0 else 100.0
        total_swcs = len(components)
        swc_coverage_pct = round((len(covered_components) / total_swcs * 100), 1) if total_swcs > 0 else 100.0

        return {
            "total_requirements": total_reqs,
            "mapped_requirements_count": len(covered_reqs),
            "unmapped_requirements_count": total_reqs - len(covered_reqs),
            "requirement_coverage_pct": req_coverage_pct,
            "swc_coverage_pct": swc_coverage_pct,
            "matrix": matrix_rows
        }
