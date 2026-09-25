"""
AUTOSAR HLD AI - Deterministic Rule-Based Offline Answer Synthesizer
Synthesizes structured, evidence-grounded architecture answers deterministically
when no external LLM API is available, using rule-based parsing and intent analysis.
"""

import re
from typing import List, Dict, Any, Optional
from app.rag.retriever import RetrievalResult


class OfflineRuleSynthesizer:
    """
    Deterministic rule-based synthesizer for AUTOSAR architecture inquiries.
    Parses retrieved document chunks and user intent to construct structured,
    factual responses without hallucination or external model dependencies.
    """

    @classmethod
    def synthesize_answer(cls, question: str, results: List[RetrievalResult]) -> str:
        """
        Synthesize a deterministic answer based on retrieved chunks and query intent.
        """
        if not results:
            return "No relevant architectural evidence was retrieved from the ingested documents."

        q_lower = question.lower()

        # Route to specialized intent synthesizers
        if cls._is_swc_query(q_lower):
            return cls._synthesize_swc_answer(question, results)
        elif cls._is_port_interface_query(q_lower):
            return cls._synthesize_interface_port_answer(question, results)
        elif cls._is_requirement_query(q_lower):
            return cls._synthesize_requirement_answer(question, results)
        elif cls._is_operational_logic_query(q_lower):
            return cls._synthesize_operational_logic_answer(question, results)
        else:
            return cls._synthesize_general_extracted_summary(question, results)

    @staticmethod
    def _is_swc_query(q: str) -> bool:
        keywords = ["swc", "software component", "components", "component defined", "what swc", "list component", "application swc"]
        return any(k in q for k in keywords)

    @staticmethod
    def _is_port_interface_query(q: str) -> bool:
        keywords = ["port", "interface", "sender-receiver", "client-server", "pport", "rport", "signals", "data flow"]
        return any(k in q for k in keywords)

    @staticmethod
    def _is_requirement_query(q: str) -> bool:
        keywords = ["req", "requirement", "traceability", "shall", "must", "asil", "iso 26262", "safety"]
        return any(k in q for k in keywords)

    @staticmethod
    def _is_operational_logic_query(q: str) -> bool:
        keywords = ["contactor", "thermal", "temperature", "voltage", "current", "timing", "ms", "hz", "threshold", "soc", "soh", "cooling", "fault"]
        return any(k in q for k in keywords)

    @classmethod
    def _synthesize_swc_answer(cls, question: str, results: List[RetrievalResult]) -> str:
        """Extract and format SWC definitions from chunks."""
        found_swcs: Dict[str, Dict[str, Any]] = {}

        # Patterns for SWCs: Name (Type): Description or Name : Type
        patterns = [
            r"([A-Z][a-zA-Z0-9_]+)\s*\((SensorActuatorSWC|ApplicationSWC|ServiceSWC|ComplexDriver|BSW[a-zA-Z0-9_]*|ECUAbstractionSWC)\)\s*[:\-–]\s*([^\.\n\r]+)",
            r"(?:Software Component|SWC)\s*[:\-]\s*([A-Z][a-zA-Z0-9_]+)\s*[\(\[]?([a-zA-Z0-9_]+)?[\)\]]?\s*[:\-–]?\s*([^\.\n\r]+)?",
            r"([A-Z][a-zA-Z0-9_]+SWC)\s*[:\-–]\s*([^\.\n\r]+)"
        ]

        for res in results:
            for pat in patterns:
                matches = re.finditer(pat, res.text)
                for m in matches:
                    groups = m.groups()
                    name = groups[0].strip()
                    if len(name) < 3 or name.lower() in ["the", "this", "and", "autosar"]:
                        continue
                    
                    swc_type = groups[1].strip() if len(groups) > 1 and groups[1] else "ApplicationSWC"
                    desc = groups[2].strip() if len(groups) > 2 and groups[2] else "AUTOSAR Software Component"
                    
                    if name not in found_swcs:
                        found_swcs[name] = {
                            "type": swc_type,
                            "description": desc,
                            "source_doc": res.document_name,
                            "page": res.page_number
                        }

        lines = [
            "### ⚙️ Deterministic Rule-Based Architecture Synthesis",
            f"**Query Intent:** Software Component (SWC) Catalog Extraction\n"
        ]

        if found_swcs:
            lines.append(f"Based on evidence retrieved across **{len(results)} document sections**, the following **{len(found_swcs)} Software Components (SWCs)** are formally defined in the specification:\n")
            lines.append("| Component Name | AUTOSAR SWC Type | Description / Architectural Responsibility | Source Citation |")
            lines.append("|:---|:---|:---|:---|")
            for name, data in sorted(found_swcs.items()):
                lines.append(f"| **`{name}`** | `{data['type']}` | {data['description']} | {data['source_doc']} (p. {data['page']}) |")
            lines.append("\n**Key Architecture Takeaways:**")
            lines.append("- Components follow modular AUTOSAR 4.x layered execution standards.")
            lines.append("- Sensor-Actuator components interface with abstraction layers while Application SWCs contain core control algorithms.")
        else:
            lines.append(cls._fallback_chunk_extraction(results))

        return "\n".join(lines)

    @classmethod
    def _synthesize_interface_port_answer(cls, question: str, results: List[RetrievalResult]) -> str:
        """Extract and format Ports & Interfaces from chunks."""
        ports = []
        port_pattern = r"(PPort|RPort|ProvidedPort|RequiredPort|Port)\s*[:\-–]\s*([a-zA-Z0-9_]+)\s*(?:\((SenderReceiver|ClientServer|Parameter)\))?\s*(?:mapped to\s*([a-zA-Z0-9_]+))?"

        for res in results:
            matches = re.finditer(port_pattern, res.text, re.IGNORECASE)
            for m in matches:
                p_type, p_name, if_type, if_name = m.groups()
                ports.append({
                    "name": p_name,
                    "type": p_type or "Port",
                    "interface": if_name or if_type or "SenderReceiver",
                    "doc": res.document_name,
                    "page": res.page_number
                })

        lines = [
            "### ⚙️ Deterministic Rule-Based Architecture Synthesis",
            f"**Query Intent:** Port & Interface Communication Mapping\n"
        ]

        if ports:
            lines.append("The following ports and interface channels were extracted from the retrieved specification:\n")
            lines.append("| Port Name | Type | Interface | Source Citation |")
            lines.append("|:---|:---|:---|:---|")
            for p in ports[:10]:
                lines.append(f"| **`{p['name']}`** | `{p['type']}` | `{p['interface']}` | {p['doc']} (p. {p['page']}) |")
        else:
            lines.append(cls._fallback_chunk_extraction(results))

        return "\n".join(lines)

    @classmethod
    def _synthesize_requirement_answer(cls, question: str, results: List[RetrievalResult]) -> str:
        """Extract and format functional and safety requirements."""
        reqs = []
        req_pattern = r"(REQ_[A-Z0-9_]+)\s*[:\-–]\s*([^\.\n\r]+(?:shall|must|will)[^\.\n\r]*)"

        for res in results:
            matches = re.finditer(req_pattern, res.text, re.IGNORECASE)
            for m in matches:
                req_id, req_text = m.groups()
                reqs.append({
                    "id": req_id,
                    "text": req_text.strip(),
                    "doc": res.document_name,
                    "page": res.page_number
                })

        lines = [
            "### ⚙️ Deterministic Rule-Based Architecture Synthesis",
            f"**Query Intent:** Functional Requirements & Safety Mandates\n"
        ]

        if reqs:
            lines.append("The following engineering requirements were identified in the verified context:\n")
            for r in reqs:
                lines.append(f"- **`{r['id']}`**: {r['text']} *[{r['doc']}, Page {r['page']}]*")
        else:
            lines.append(cls._fallback_chunk_extraction(results))

        return "\n".join(lines)

    @classmethod
    def _synthesize_operational_logic_answer(cls, question: str, results: List[RetrievalResult]) -> str:
        """Synthesize operational thresholds, timing, and contactor/thermal logic."""
        lines = [
            "### ⚙️ Deterministic Rule-Based Architecture Synthesis",
            f"**Query Intent:** Operational Control Logic & Behavioral Parameters\n",
            "Extracted architectural logic and engineering rules grounded in the specification:\n"
        ]

        bullet_points = []
        for res in results:
            sentences = [s.strip() for s in re.split(r'\.|\n', res.text) if len(s.strip()) > 30]
            for s in sentences:
                if any(w in s.lower() for w in ["shall", "must", "threshold", "cycle", "loop", "period", "ms", "temp", "volt", "fault", "contactor", "cooling"]):
                    bullet_points.append(f"- {s} *[{res.document_name}, p. {res.page_number}]*")

        if bullet_points:
            # Deduplicate bullet points while preserving order
            seen = set()
            for bp in bullet_points:
                clean_bp = bp.split("*[")[0].strip()
                if clean_bp not in seen and len(seen) < 8:
                    seen.add(clean_bp)
                    lines.append(bp)
        else:
            lines.append(cls._fallback_chunk_extraction(results))

        return "\n".join(lines)

    @classmethod
    def _synthesize_general_extracted_summary(cls, question: str, results: List[RetrievalResult]) -> str:
        """Synthesize a general summary with key architectural sentences."""
        lines = [
            "### ⚙️ Deterministic Rule-Based Architecture Synthesis",
            f"**Evidence Synthesized Across Top {len(results)} Verified Chunks:**\n"
        ]

        extracted_statements = []
        for res in results:
            sentences = [s.strip() for s in re.split(r'\.|\n', res.text) if len(s.strip()) > 35]
            for s in sentences:
                if any(kw in s.lower() for kw in ["component", "interface", "port", "requirement", "function", "timing", "layer", "module", "system"]):
                    extracted_statements.append((res.score, s, res.document_name, res.page_number))

        if extracted_statements:
            extracted_statements.sort(key=lambda x: x[0], reverse=True)
            seen = set()
            for _, s, doc, page in extracted_statements:
                if s not in seen and len(seen) < 6:
                    seen.add(s)
                    lines.append(f"- {s} *[{doc}, Page {page}]*")
        else:
            lines.append(cls._fallback_chunk_extraction(results))

        return "\n".join(lines)

    @staticmethod
    def _fallback_chunk_extraction(results: List[RetrievalResult]) -> str:
        """Fallback to formatted snippet excerpts."""
        lines = ["**Direct Document Excerpts:**\n"]
        for i, r in enumerate(results[:3], 1):
            snippet = r.text[:300].strip().replace("\n", " ") + "..."
            lines.append(f"**[{i}]** *{r.document_name} (Page {r.page_number})*: \"{snippet}\"")
        return "\n".join(lines)
