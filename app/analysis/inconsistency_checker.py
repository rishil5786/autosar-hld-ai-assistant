"""
AUTOSAR HLD AI - Inconsistency & Architecture Compliance Auditor
Performs rigorous structural and semantic checks to identify inconsistencies,
missing dependencies, layer violations, and dangling ports in AUTOSAR HLD documents.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import re
from app.utils.logger import logger


class InconsistencyChecker:
    """
    Automated rule-based and semantic validation engine for AUTOSAR HLD architectures.
    """

    def __init__(self):
        pass

    def check_document(
        self,
        document_id: str,
        components: List[Dict[str, Any]],
        interfaces: List[Dict[str, Any]],
        ports: List[Dict[str, Any]],
        signals: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run full suite of AUTOSAR architecture consistency audits.

        Returns:
            Dictionary containing audit summary, metrics, and detailed findings list.
        """
        logger.info(f"Running inconsistency and compliance audit for document {document_id}")

        findings = []

        # 1. Check Unconnected / Missing Ports
        findings.extend(self._check_unconnected_ports(ports, interfaces))

        # 2. Check Missing Interface Definitions
        findings.extend(self._check_missing_interfaces(ports, interfaces))

        # 3. Check Layer Boundary Violations
        findings.extend(self._check_layer_violations(components, dependencies))

        # 4. Check Orphaned Components (isolated SWCs with no connections)
        findings.extend(self._check_orphaned_components(components, ports, dependencies))

        # 5. Check Cyclic Dependencies
        findings.extend(self._check_cyclic_dependencies(dependencies))

        # 6. Check Naming Convention Compliance
        findings.extend(self._check_naming_conventions(components, ports, interfaces))

        # 7. Check Incomplete Port / Interface Metadata
        findings.extend(self._check_incomplete_specifications(ports, interfaces))

        # Categorize by severity
        critical_count = sum(1 for f in findings if f["severity"] == "CRITICAL")
        high_count = sum(1 for f in findings if f["severity"] == "HIGH")
        warning_count = sum(1 for f in findings if f["severity"] == "WARNING")
        info_count = sum(1 for f in findings if f["severity"] == "INFO")

        # Compute Architecture Health Score (0 - 100)
        penalty = (critical_count * 25) + (high_count * 15) + (warning_count * 5) + (info_count * 1)
        health_score = max(0, min(100, 100 - penalty))

        return {
            "document_id": document_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "health_score": health_score,
            "total_findings": len(findings),
            "critical_count": critical_count,
            "high_count": high_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "findings": findings
        }

    def _check_unconnected_ports(
        self,
        ports: List[Dict[str, Any]],
        interfaces: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify Provided ports without matching Required ports or vice versa."""
        findings = []
        
        # Group ports by interface name
        interface_pports = {}
        interface_rports = {}

        for p in ports:
            if_name = p.get("interface_name")
            p_type = (p.get("port_type") or "").lower()
            p_dir = (p.get("direction") or "").lower()

            if not if_name:
                continue

            is_provided = "prov" in p_type or "out" in p_dir or "p-port" in p_type or "pport" in p_type
            is_required = "req" in p_type or "in" in p_dir or "r-port" in p_type or "rport" in p_type

            if is_provided:
                interface_pports.setdefault(if_name, []).append(p)
            if is_required:
                interface_rports.setdefault(if_name, []).append(p)

        # Look for Required ports that have NO matching Provider
        for if_name, req_list in interface_rports.items():
            if if_name not in interface_pports or len(interface_pports[if_name]) == 0:
                for rp in req_list:
                    findings.append({
                        "category": "Unconnected Port (Missing Provider)",
                        "severity": "CRITICAL",
                        "title": f"Unsatisfied Required Port: {rp.get('name')} in {rp.get('component_name')}",
                        "description": f"Component '{rp.get('component_name')}' expects interface '{if_name}' via port '{rp.get('name')}', but no component provides this interface.",
                        "recommendation": f"Define a PPort with interface '{if_name}' on the corresponding producer SWC or BSW module.",
                        "source_page": rp.get("source_page")
                    })

        # Look for Provided ports with no consumer
        for if_name, prov_list in interface_pports.items():
            if if_name not in interface_rports or len(interface_rports[if_name]) == 0:
                for pp in prov_list:
                    findings.append({
                        "category": "Unconsumed Provided Port",
                        "severity": "WARNING",
                        "title": f"Unconsumed Provided Port: {pp.get('name')} in {pp.get('component_name')}",
                        "description": f"Component '{pp.get('component_name')}' provides interface '{if_name}' via port '{pp.get('name')}', but no consumer SWC requires it.",
                        "recommendation": f"Verify if interface '{if_name}' is intended for diagnostic/calibration tools, or remove unused port.",
                        "source_page": pp.get("source_page")
                    })

        return findings

    def _check_missing_interfaces(
        self,
        ports: List[Dict[str, Any]],
        interfaces: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Check for ports referencing interfaces not defined in the document."""
        findings = []
        known_interfaces = {i.get("name", "").strip().lower() for i in interfaces if i.get("name")}

        for p in ports:
            if_name = p.get("interface_name")
            if if_name and if_name.strip().lower() not in known_interfaces:
                findings.append({
                    "category": "Undefined Interface",
                    "severity": "HIGH",
                    "title": f"Port '{p.get('name')}' references undefined interface '{if_name}'",
                    "description": f"Component '{p.get('component_name')}' defines port '{p.get('name')}' using interface '{if_name}', but this interface specification is missing in the document.",
                    "recommendation": f"Add the formal interface definition for '{if_name}' including data elements and methods.",
                    "source_page": p.get("source_page")
                })

        return findings

    def _check_layer_violations(
        self,
        components: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Check for AUTOSAR Layer architecture violations (e.g., Application SWC
        bypassing RTE / Service layer and accessing MCAL or Hardware directly).
        """
        findings = []

        mcal_keywords = ["mcal", "driver", "dio", "adc", "spi", "pwm", "can_drv", "hal", "register"]

        for dep in dependencies:
            src = dep.get("source_component", "")
            tgt = dep.get("target_component", "")

            # Check if source is Application SWC and target is low-level driver
            is_app_swc = any(kw in src.lower() for kw in ["app", "control", "calc", "manager", "algorithm", "fusion"])
            is_mcal_target = any(kw in tgt.lower() for kw in mcal_keywords) and not any(kw in tgt.lower() for kw in ["service", "rte", "interface"])

            if is_app_swc and is_mcal_target:
                findings.append({
                    "category": "AUTOSAR Layer Violation",
                    "severity": "CRITICAL",
                    "title": f"Layer Violation: '{src}' direct dependency on low-level '{tgt}'",
                    "description": f"Application component '{src}' has direct architectural coupling to driver/MCAL component '{tgt}'. In AUTOSAR, Application SWCs must communicate exclusively via RTE and BSW Services (e.g. IoHwAb or SensorActuatorSWC).",
                    "recommendation": f"Introduce an ECU Abstraction SWC (IoHwAb) or Service Port to decouple application logic from hardware drivers.",
                    "source_page": dep.get("source_page")
                })

        return findings

    def _check_orphaned_components(
        self,
        components: List[Dict[str, Any]],
        ports: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify isolated components with zero ports and zero dependencies."""
        findings = []
        components_with_ports = {p.get("component_name", "").strip() for p in ports if p.get("component_name")}
        components_with_deps = set()
        for d in dependencies:
            if d.get("source_component"):
                components_with_deps.add(d["source_component"].strip())
            if d.get("target_component"):
                components_with_deps.add(d["target_component"].strip())

        for c in components:
            c_name = c.get("name", "").strip()
            if not c_name:
                continue
            
            has_ports = c_name in components_with_ports
            has_deps = c_name in components_with_deps

            if not has_ports and not has_deps:
                findings.append({
                    "category": "Orphaned Component",
                    "severity": "WARNING",
                    "title": f"Orphaned Component: '{c_name}'",
                    "description": f"Component '{c_name}' is declared in the document but has no associated ports, interfaces, or dependency connections.",
                    "recommendation": f"Verify if '{c_name}' ports are documented in a separate subsystem document or remove unused component stub.",
                    "source_page": c.get("source_page")
                })

        return findings

    def _check_cyclic_dependencies(
        self,
        dependencies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect circular dependencies between components using DFS cycle detection."""
        findings = []
        adj = {}
        for d in dependencies:
            u = d.get("source_component")
            v = d.get("target_component")
            if u and v:
                adj.setdefault(u, set()).add(v)

        visited = {}  # 0: unvisited, 1: visiting, 2: visited
        parent_map = {}

        def dfs(node, path):
            visited[node] = 1
            for neighbor in adj.get(node, []):
                if visited.get(neighbor) == 1:
                    # Cycle found
                    cycle_start_idx = path.index(neighbor) if neighbor in path else 0
                    cycle_path = path[cycle_start_idx:] + [neighbor]
                    cycle_str = " -> ".join(cycle_path)
                    findings.append({
                        "category": "Cyclic Architecture Dependency",
                        "severity": "CRITICAL",
                        "title": f"Circular Dependency: {cycle_str}",
                        "description": f"Components form a circular dependency loop ({cycle_str}). This causes RTE execution ordering issues and tightly couples components.",
                        "recommendation": "Refactor communication to use asynchronous event notifications or an intermediary coordinator component.",
                        "source_page": None
                    })
                elif visited.get(neighbor, 0) == 0:
                    dfs(neighbor, path + [neighbor])
            visited[node] = 2

        for node in list(adj.keys()):
            if visited.get(node, 0) == 0:
                dfs(node, [node])

        return findings

    def _check_naming_conventions(
        self,
        components: List[Dict[str, Any]],
        ports: List[Dict[str, Any]],
        interfaces: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Validate AUTOSAR naming conventions (PascalCase, prefixing, port naming)."""
        findings = []

        # Check Component naming
        for c in components:
            name = c.get("name", "")
            if name and not re.match(r'^[A-Z][a-zA-Z0-9_]+$', name):
                findings.append({
                    "category": "Naming Convention",
                    "severity": "INFO",
                    "title": f"Component name '{name}' deviates from AUTOSAR standard",
                    "description": f"Component '{name}' does not follow UpperCamelCase standard AUTOSAR identifier conventions.",
                    "recommendation": f"Rename '{name}' to follow standard AUTOSAR PascalCase naming.",
                    "source_page": c.get("source_page")
                })

        # Check Interface naming
        for iface in interfaces:
            name = iface.get("name", "")
            if name and not (name.startswith("If_") or name.startswith("I_") or name.startswith("Interface_") or name.startswith("I") or name.isupper() or re.match(r'^[A-Z][a-zA-Z0-9_]+Interface$', name)):
                findings.append({
                    "category": "Naming Convention",
                    "severity": "INFO",
                    "title": f"Interface name '{name}' does not follow AUTOSAR naming pattern",
                    "description": f"Interface '{name}' is missing standard interface prefix/suffix (e.g. 'If_Xxx' or 'Xxx_I').",
                    "recommendation": f"Format interface name as 'If_{name}' or '{name}_I'.",
                    "source_page": iface.get("source_page")
                })

        # Check Port naming (P_xxx or R_xxx or pPort_xxx)
        for p in ports:
            p_name = p.get("name", "")
            p_type = (p.get("port_type") or "").lower()
            if p_name:
                is_p_port = "prov" in p_type or "p-port" in p_type or "pport" in p_type
                is_r_port = "req" in p_type or "r-port" in p_type or "rport" in p_type

                if is_p_port and not (p_name.startswith("P_") or p_name.startswith("Pp_") or p_name.startswith("p_") or "prov" in p_name.lower()):
                    findings.append({
                        "category": "Naming Convention",
                        "severity": "INFO",
                        "title": f"Provided Port '{p_name}' missing 'P_' prefix",
                        "description": f"Provided port '{p_name}' in '{p.get('component_name')}' should follow standard AUTOSAR port prefix 'P_'.",
                        "recommendation": f"Rename port to 'P_{p_name}'.",
                        "source_page": p.get("source_page")
                    })
                elif is_r_port and not (p_name.startswith("R_") or p_name.startswith("Pr_") or p_name.startswith("r_") or "req" in p_name.lower()):
                    findings.append({
                        "category": "Naming Convention",
                        "severity": "INFO",
                        "title": f"Required Port '{p_name}' missing 'R_' prefix",
                        "description": f"Required port '{p_name}' in '{p.get('component_name')}' should follow standard AUTOSAR port prefix 'R_'.",
                        "recommendation": f"Rename port to 'R_{p_name}'.",
                        "source_page": p.get("source_page")
                    })

        return findings

    def _check_incomplete_specifications(
        self,
        ports: List[Dict[str, Any]],
        interfaces: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Check for ports missing types or interfaces missing descriptions/categories."""
        findings = []

        for p in ports:
            if not p.get("port_type"):
                findings.append({
                    "category": "Incomplete Specification",
                    "severity": "WARNING",
                    "title": f"Port '{p.get('name')}' is missing port type specification",
                    "description": f"Port '{p.get('name')}' in component '{p.get('component_name')}' does not specify whether it is a Provided (PPort) or Required (RPort).",
                    "recommendation": "Specify port direction / type explicitly (Provided or Required).",
                    "source_page": p.get("source_page")
                })

        for i in interfaces:
            if not i.get("interface_type"):
                findings.append({
                    "category": "Incomplete Specification",
                    "severity": "WARNING",
                    "title": f"Interface '{i.get('name')}' missing interface type classification",
                    "description": f"Interface '{i.get('name')}' is missing type classification (e.g. Sender-Receiver, Client-Server, Parameter, Mode-Switch).",
                    "recommendation": "Classify interface as Sender-Receiver (S/R) or Client-Server (C/S).",
                    "source_page": i.get("source_page")
                })

        return findings
