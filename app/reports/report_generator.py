"""
AUTOSAR HLD AI - Report Generator
Generates comprehensive engineering reports in Markdown, HTML, and formatted text.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.utils.logger import logger


class ReportGenerator:
    """
    Produces formal engineering reports for AUTOSAR HLD analysis.
    """

    @staticmethod
    def generate_architecture_summary_report(
        doc_metadata: Dict[str, Any],
        components: List[Dict[str, Any]],
        interfaces: List[Dict[str, Any]],
        ports: List[Dict[str, Any]],
        signals: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]],
        audit_summary: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a complete Markdown Architecture Design Assessment Report."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        doc_name = doc_metadata.get("filename", "AUTOSAR_HLD_Document")
        doc_ver = doc_metadata.get("version", "1.0")

        lines = [
            f"# AUTOSAR High-Level Design (HLD) Architecture Assessment Report",
            f"**Document Name:** `{doc_name}` | **Version:** `{doc_ver}` | **Generated:** `{now}`",
            f"**Classification:** Internal Engineering Report | **Status:** AI-Analyzed (Human Approval Required)",
            "",
            "---",
            "",
            "## 1. Executive Summary",
            f"This report presents an automated structural and architectural analysis of `{doc_name}`.",
            f"A total of **{len(components)} Software Components (SWCs)**, **{len(interfaces)} Port Interfaces**, **{len(ports)} Ports**, and **{len(dependencies)} Inter-component Dependencies** were identified.",
            "",
        ]

        if audit_summary:
            health = audit_summary.get("health_score", 100)
            crit = audit_summary.get("critical_count", 0)
            high = audit_summary.get("high_count", 0)
            warn = audit_summary.get("warning_count", 0)
            lines.extend([
                "### Architecture Health Metrics",
                f"- **Overall Architecture Health Score:** `{health}/100`",
                f"- **Critical Architecture Mismatches:** `{crit}`",
                f"- **High Priority Issues:** `{high}`",
                f"- **Warnings / Best Practice Notes:** `{warn}`",
                ""
            ])

        lines.extend([
            "---",
            "",
            "## 2. Software Component (SWC) Inventory",
            "| Component Name | Type | Source Page | Confidence | Description |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ])

        for c in components:
            desc = (c.get("description") or "N/A").replace("|", "-")
            desc = desc[:80] + "..." if len(desc) > 80 else desc
            lines.append(f"| **{c.get('name')}** | {c.get('component_type', 'SWC')} | Pg. {c.get('source_page', '-')} | {round(c.get('confidence', 1.0)*100)}% | {desc} |")

        lines.extend([
            "",
            "---",
            "",
            "## 3. Port Interfaces Inventory",
            "| Interface Name | Type | Related Component | Source Page |",
            "| :--- | :--- | :--- | :--- |"
        ])

        for i in interfaces:
            lines.append(f"| **{i.get('name')}** | {i.get('interface_type', 'SenderReceiver')} | {i.get('related_component', '-')} | Pg. {i.get('source_page', '-')} |")

        lines.extend([
            "",
            "---",
            "",
            "## 4. Port Allocations",
            "| Port Name | Component | Direction / Type | Interface | Source Page |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ])

        for p in ports:
            lines.append(f"| **{p.get('name')}** | {p.get('component_name', '-')} | {p.get('port_type', 'Provided')} ({p.get('direction', 'Out')}) | `{p.get('interface_name', '-')}` | Pg. {p.get('source_page', '-')} |")

        lines.extend([
            "",
            "---",
            "",
            "## 5. Governance & AI Accountability Notice",
            "> **ISO 26262 / ASPICE Governance Principle:**",
            "> AI-extracted architecture items and findings must be reviewed and formally signed off by a certified AUTOSAR System Architect before inclusion in baseline software releases or safety cases.",
            ""
        ])

        return "\n".join(lines)

    @staticmethod
    def generate_revision_comparison_report(diff_data: Dict[str, Any]) -> str:
        """Generate a Markdown Revision Diff & Impact Analysis Report."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        v1 = diff_data.get("v1_version", "v1.0")
        v2 = diff_data.get("v2_version", "v2.0")

        lines = [
            f"# AUTOSAR HLD Revision Comparison & Impact Report",
            f"**Baseline Version:** `{v1}` ➔ **Target Version:** `{v2}` | **Generated:** `{now}`",
            "",
            "---",
            "",
            "## 1. Evolution Summary",
            f"{diff_data.get('evolution_summary', 'No summary generated.')}",
            "",
            f"- **Total Architectural Changes:** `{diff_data.get('total_changes_count', 0)}`",
            f"- **Breaking Changes Flagged:** `{diff_data.get('breaking_changes_count', 0)}`",
            "",
            "---",
            "",
            "## 2. Breaking Changes & Integration Risks",
        ]

        breaking = diff_data.get("breaking_changes", [])
        if breaking:
            lines.extend([
                "| Category | Severity | Item | Impact | Details |",
                "| :--- | :--- | :--- | :--- | :--- |"
            ])
            for b in breaking:
                lines.append(f"| {b.get('category')} | `{b.get('severity')}` | **{b.get('item')}** | {b.get('impact')} | {b.get('description')} |")
        else:
            lines.append("_No breaking architectural changes identified between revisions._\n")

        # Component changes
        comp_diff = diff_data.get("components", {})
        lines.extend([
            "",
            "---",
            "",
            "## 3. Component Modifications",
            f"- **Added Components:** {len(comp_diff.get('added', []))}",
            f"- **Removed Components:** {len(comp_diff.get('removed', []))}",
            f"- **Modified Components:** {len(comp_diff.get('modified', []))}",
            ""
        ])

        if comp_diff.get("added"):
            lines.append("### Introduced Components (Added)")
            for c in comp_diff["added"]:
                lines.append(f"- `+` **{c.get('name')}** ({c.get('component_type', 'SWC')}): {c.get('description', '')}")

        if comp_diff.get("removed"):
            lines.append("\n### Decommissioned Components (Removed)")
            for c in comp_diff["removed"]:
                lines.append(f"- `-` **{c.get('name')}** ({c.get('component_type', 'SWC')})")

        return "\n".join(lines)
