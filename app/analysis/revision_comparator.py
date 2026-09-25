"""
AUTOSAR HLD AI - Revision Comparator
Compares two versions/revisions of AUTOSAR HLD documents to identify structural,
interface, component, and semantic architectural changes.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import difflib
from app.utils.logger import logger


class RevisionComparator:
    """
    Compares two AUTOSAR HLD document revisions and produces detailed diff reports.
    """

    def __init__(self):
        pass

    def compare_documents(
        self,
        doc_v1_data: Dict[str, Any],
        doc_v2_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare two document extractions / metadata.

        Args:
            doc_v1_data: Dict containing v1 metadata, components, interfaces, ports, signals, dependencies
            doc_v2_data: Dict containing v2 metadata, components, interfaces, ports, signals, dependencies

        Returns:
            Structured comparison report dictionary.
        """
        logger.info(f"Comparing revision '{doc_v1_data.get('version', 'v1')}' with '{doc_v2_data.get('version', 'v2')}'")

        # 1. Compare Components
        component_diff = self._compare_components(
            doc_v1_data.get("components", []),
            doc_v2_data.get("components", [])
        )

        # 2. Compare Interfaces
        interface_diff = self._compare_interfaces(
            doc_v1_data.get("interfaces", []),
            doc_v2_data.get("interfaces", [])
        )

        # 3. Compare Ports
        port_diff = self._compare_ports(
            doc_v1_data.get("ports", []),
            doc_v2_data.get("ports", [])
        )

        # 4. Compare Signals
        signal_diff = self._compare_signals(
            doc_v1_data.get("signals", []),
            doc_v2_data.get("signals", [])
        )

        # 5. Compare Dependencies
        dependency_diff = self._compare_dependencies(
            doc_v1_data.get("dependencies", []),
            doc_v2_data.get("dependencies", [])
        )

        # 6. Identify Breaking Changes
        breaking_changes = self._identify_breaking_changes(
            component_diff, interface_diff, port_diff
        )

        # 7. Compute Architecture Evolution Metrics
        total_changes = (
            len(component_diff["added"]) + len(component_diff["removed"]) + len(component_diff["modified"]) +
            len(interface_diff["added"]) + len(interface_diff["removed"]) + len(interface_diff["modified"]) +
            len(port_diff["added"]) + len(port_diff["removed"]) + len(port_diff["modified"])
        )

        summary = {
            "v1_version": doc_v1_data.get("version", "v1.0"),
            "v2_version": doc_v2_data.get("version", "v2.0"),
            "v1_filename": doc_v1_data.get("filename", "Document_v1.pdf"),
            "v2_filename": doc_v2_data.get("filename", "Document_v2.pdf"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_changes_count": total_changes,
            "breaking_changes_count": len(breaking_changes),
            "breaking_changes": breaking_changes,
            "components": component_diff,
            "interfaces": interface_diff,
            "ports": port_diff,
            "signals": signal_diff,
            "dependencies": dependency_diff,
            "evolution_summary": self._generate_evolution_summary(
                doc_v1_data.get("version", "v1.0"),
                doc_v2_data.get("version", "v2.0"),
                component_diff,
                interface_diff,
                breaking_changes
            )
        }

        return summary

    def _compare_components(self, v1_items: List[Dict], v2_items: List[Dict]) -> Dict[str, Any]:
        v1_map = {item.get("name", "").strip(): item for item in v1_items if item.get("name")}
        v2_map = {item.get("name", "").strip(): item for item in v2_items if item.get("name")}

        v1_names = set(v1_map.keys())
        v2_names = set(v2_map.keys())

        added_names = v2_names - v1_names
        removed_names = v1_names - v2_names
        common_names = v1_names & v2_names

        added = [v2_map[n] for n in sorted(added_names)]
        removed = [v1_map[n] for n in sorted(removed_names)]
        modified = []

        for name in sorted(common_names):
            c1 = v1_map[name]
            c2 = v2_map[name]
            changes = {}

            if c1.get("component_type") != c2.get("component_type"):
                changes["component_type"] = {
                    "old": c1.get("component_type"),
                    "new": c2.get("component_type")
                }
            
            d1 = (c1.get("description") or "").strip()
            d2 = (c2.get("description") or "").strip()
            if d1 != d2 and len(d1) > 0 and len(d2) > 0:
                changes["description"] = {
                    "old": d1,
                    "new": d2,
                    "diff": list(difflib.unified_diff(d1.splitlines(), d2.splitlines(), lineterm=""))
                }

            if changes:
                modified.append({
                    "name": name,
                    "changes": changes,
                    "v1_details": c1,
                    "v2_details": c2
                })

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "unchanged_count": len(common_names) - len(modified)
        }

    def _compare_interfaces(self, v1_items: List[Dict], v2_items: List[Dict]) -> Dict[str, Any]:
        v1_map = {item.get("name", "").strip(): item for item in v1_items if item.get("name")}
        v2_map = {item.get("name", "").strip(): item for item in v2_items if item.get("name")}

        v1_names = set(v1_map.keys())
        v2_names = set(v2_map.keys())

        added_names = v2_names - v1_names
        removed_names = v1_names - v2_names
        common_names = v1_names & v2_names

        added = [v2_map[n] for n in sorted(added_names)]
        removed = [v1_map[n] for n in sorted(removed_names)]
        modified = []

        for name in sorted(common_names):
            i1 = v1_map[name]
            i2 = v2_map[name]
            changes = {}

            if i1.get("interface_type") != i2.get("interface_type"):
                changes["interface_type"] = {
                    "old": i1.get("interface_type"),
                    "new": i2.get("interface_type")
                }

            if i1.get("related_component") != i2.get("related_component"):
                changes["related_component"] = {
                    "old": i1.get("related_component"),
                    "new": i2.get("related_component")
                }

            if changes:
                modified.append({
                    "name": name,
                    "changes": changes,
                    "v1_details": i1,
                    "v2_details": i2
                })

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "unchanged_count": len(common_names) - len(modified)
        }

    def _compare_ports(self, v1_items: List[Dict], v2_items: List[Dict]) -> Dict[str, Any]:
        def port_key(p):
            return f"{p.get('component_name', '')}::{p.get('name', '')}"

        v1_map = {port_key(p): p for p in v1_items if p.get("name")}
        v2_map = {port_key(p): p for p in v2_items if p.get("name")}

        v1_keys = set(v1_map.keys())
        v2_keys = set(v2_map.keys())

        added = [v2_map[k] for k in sorted(v2_keys - v1_keys)]
        removed = [v1_map[k] for k in sorted(v1_keys - v2_keys)]
        modified = []

        for k in sorted(v1_keys & v2_keys):
            p1 = v1_map[k]
            p2 = v2_map[k]
            changes = {}

            if p1.get("port_type") != p2.get("port_type"):
                changes["port_type"] = {"old": p1.get("port_type"), "new": p2.get("port_type")}
            if p1.get("interface_name") != p2.get("interface_name"):
                changes["interface_name"] = {"old": p1.get("interface_name"), "new": p2.get("interface_name")}
            if p1.get("direction") != p2.get("direction"):
                changes["direction"] = {"old": p1.get("direction"), "new": p2.get("direction")}

            if changes:
                modified.append({
                    "key": k,
                    "name": p2.get("name"),
                    "component": p2.get("component_name"),
                    "changes": changes
                })

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "unchanged_count": len(v1_keys & v2_keys) - len(modified)
        }

    def _compare_signals(self, v1_items: List[Dict], v2_items: List[Dict]) -> Dict[str, Any]:
        v1_map = {s.get("name", ""): s for s in v1_items if s.get("name")}
        v2_map = {s.get("name", ""): s for s in v2_items if s.get("name")}

        v1_names = set(v1_map.keys())
        v2_names = set(v2_map.keys())

        added = [v2_map[n] for n in sorted(v2_names - v1_names)]
        removed = [v1_map[n] for n in sorted(v1_names - v2_names)]
        modified = []

        for n in sorted(v1_names & v2_names):
            s1 = v1_map[n]
            s2 = v2_map[n]
            changes = {}
            if s1.get("signal_type") != s2.get("signal_type"):
                changes["signal_type"] = {"old": s1.get("signal_type"), "new": s2.get("signal_type")}
            if s1.get("source_component") != s2.get("source_component") or s1.get("target_component") != s2.get("target_component"):
                changes["routing"] = {
                    "old": f"{s1.get('source_component')} -> {s1.get('target_component')}",
                    "new": f"{s2.get('source_component')} -> {s2.get('target_component')}"
                }
            if changes:
                modified.append({"name": n, "changes": changes})

        return {"added": added, "removed": removed, "modified": modified}

    def _compare_dependencies(self, v1_items: List[Dict], v2_items: List[Dict]) -> Dict[str, Any]:
        def dep_key(d):
            return f"{d.get('source_component')} -> {d.get('target_component')}"

        v1_map = {dep_key(d): d for d in v1_items if d.get("source_component") and d.get("target_component")}
        v2_map = {dep_key(d): d for d in v2_items if d.get("source_component") and d.get("target_component")}

        v1_keys = set(v1_map.keys())
        v2_keys = set(v2_map.keys())

        added = [v2_map[k] for k in sorted(v2_keys - v1_keys)]
        removed = [v1_map[k] for k in sorted(v1_keys - v2_keys)]

        return {"added": added, "removed": removed}

    def _identify_breaking_changes(
        self,
        comp_diff: Dict[str, Any],
        if_diff: Dict[str, Any],
        port_diff: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify potential breaking architecture changes between revisions."""
        breaking = []

        # 1. Removed components
        for c in comp_diff.get("removed", []):
            breaking.append({
                "category": "Component Deletion",
                "severity": "CRITICAL",
                "item": c.get("name"),
                "description": f"Component '{c.get('name')}' was removed. Any dependent SWCs or RTE connections will break.",
                "impact": "High - Integration failure in downstream ECUs"
            })

        # 2. Removed interfaces
        for i in if_diff.get("removed", []):
            breaking.append({
                "category": "Interface Deletion",
                "severity": "CRITICAL",
                "item": i.get("name"),
                "description": f"Interface '{i.get('name')}' was removed from architecture.",
                "impact": "High - Port mappings referencing this interface will become invalid"
            })

        # 3. Modified interface types
        for m in if_diff.get("modified", []):
            if "interface_type" in m.get("changes", {}):
                breaking.append({
                    "category": "Interface Signature Change",
                    "severity": "HIGH",
                    "item": m.get("name"),
                    "description": f"Interface '{m.get('name')}' type changed from {m['changes']['interface_type']['old']} to {m['changes']['interface_type']['new']}.",
                    "impact": "Medium - Requires RTE generator re-run and code regeneration"
                })

        # 4. Removed or modified ports
        for p in port_diff.get("removed", []):
            breaking.append({
                "category": "Port Deletion",
                "severity": "HIGH",
                "item": p.get("name"),
                "description": f"Port '{p.get('name')}' removed from component '{p.get('component_name')}'.",
                "impact": "Medium - Unresolved assembly connector in composition"
            })

        return breaking

    def _generate_evolution_summary(
        self,
        v1: str,
        v2: str,
        comp_diff: Dict,
        if_diff: Dict,
        breaking: List[Dict]
    ) -> str:
        """Create a human-readable engineering narrative of the changes."""
        added_c = len(comp_diff.get("added", []))
        rem_c = len(comp_diff.get("removed", []))
        mod_c = len(comp_diff.get("modified", []))
        added_i = len(if_diff.get("added", []))

        narrative = (
            f"Architecture Evolution from {v1} to {v2}: "
            f"{added_c} new components introduced, {rem_c} components decommissioned, and {mod_c} modified. "
            f"{added_i} new interfaces created. "
            f"Detected {len(breaking)} potential breaking architectural changes requiring team review."
        )
        return narrative
