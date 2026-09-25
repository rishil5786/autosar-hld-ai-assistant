"""
AUTOSAR HLD AI - Export Service
Generates ARXML skeletons, Mermaid diagrams, JSON, and CSV exports from extracted architecture.
"""

from typing import List, Dict, Any, Optional
import json
import csv
import io
import xml.etree.ElementTree as ET
from xml.dom import minidom
from app.utils.logger import logger


class ExportService:
    """
    Handles generation of AUTOSAR ARXML, architecture diagrams, and tabular exports.
    """

    @staticmethod
    def generate_arxml(
        components: List[Dict[str, Any]],
        interfaces: List[Dict[str, Any]],
        ports: List[Dict[str, Any]],
        project_name: str = "AUTOSAR_System"
    ) -> str:
        """
        Generate standard AUTOSAR 4.x compliant ARXML XML representation.
        """
        logger.info(f"Generating ARXML for {len(components)} components and {len(interfaces)} interfaces")

        root = ET.Element("AUTOSAR", {
            "xmlns": "http://autosar.org/schema/r4.0",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": "http://autosar.org/schema/r4.0 AUTOSAR_4-3-0.xsd"
        })

        ar_packages = ET.SubElement(root, "AR-PACKAGES")

        # Package 1: Interfaces
        if_pkg = ET.SubElement(ar_packages, "AR-PACKAGE")
        ET.SubElement(if_pkg, "SHORT-NAME").text = "PortInterfaces"
        if_elements = ET.SubElement(if_pkg, "ELEMENTS")

        for iface in interfaces:
            if_name = iface.get("name", "UnknownInterface").replace(" ", "_")
            if_type = (iface.get("interface_type") or "SenderReceiver").lower()

            tag = "CLIENT-SERVER-INTERFACE" if "client" in if_type or "server" in if_type else "SENDER-RECEIVER-INTERFACE"
            elem = ET.SubElement(if_elements, tag)
            ET.SubElement(elem, "SHORT-NAME").text = if_name
            ET.SubElement(elem, "IS-SERVICE").text = "false"
            
            if tag == "SENDER-RECEIVER-INTERFACE":
                data_elements = ET.SubElement(elem, "DATA-ELEMENTS")
                v_elem = ET.SubElement(data_elements, "VARIABLE-DATA-PROTOTYPE")
                ET.SubElement(v_elem, "SHORT-NAME").text = f"Val_{if_name}"
                type_ref = ET.SubElement(v_elem, "TYPE-TREF", {"DEST": "IMPLEMENTATION-DATA-TYPE"})
                type_ref.text = "/AUTOSAR_Platform/ImplementationDataTypes/uint32"
            else:
                ops = ET.SubElement(elem, "OPERATIONS")
                op = ET.SubElement(ops, "CLIENT-SERVER-OPERATION")
                ET.SubElement(op, "SHORT-NAME").text = f"Op_{if_name}"

        # Package 2: Component Types
        swc_pkg = ET.SubElement(ar_packages, "AR-PACKAGE")
        ET.SubElement(swc_pkg, "SHORT-NAME").text = "ComponentTypes"
        swc_elements = ET.SubElement(swc_pkg, "ELEMENTS")

        # Map ports to components
        ports_by_comp = {}
        for p in ports:
            c_name = p.get("component_name", "DefaultComponent")
            ports_by_comp.setdefault(c_name, []).append(p)

        for comp in components:
            c_name = comp.get("name", "SWC_Generic").replace(" ", "_")
            c_type = (comp.get("component_type") or "Application").lower()

            tag = "SENSOR-ACTUATOR-SW-COMPONENT-TYPE" if "sensor" in c_type or "actuator" in c_type else "APPLICATION-SW-COMPONENT-TYPE"
            comp_elem = ET.SubElement(swc_elements, tag)
            ET.SubElement(comp_elem, "SHORT-NAME").text = c_name

            # Add Ports
            c_ports = ports_by_comp.get(c_name, [])
            if c_ports:
                ports_elem = ET.SubElement(comp_elem, "PORTS")
                for p in c_ports:
                    p_name = p.get("name", "Port_1").replace(" ", "_")
                    p_type = (p.get("port_type") or "provided").lower()
                    p_iface = p.get("interface_name") or f"If_{p_name}"

                    is_provided = "prov" in p_type or "p-port" in p_type or "pport" in p_type or p_name.startswith("P_")
                    port_tag = "P-PORT-PROTOTYPE" if is_provided else "R-PORT-PROTOTYPE"
                    if_dest_tag = "PROVIDED-INTERFACE-TREF" if is_provided else "REQUIRED-INTERFACE-TREF"

                    p_prototype = ET.SubElement(ports_elem, port_tag)
                    ET.SubElement(p_prototype, "SHORT-NAME").text = p_name
                    if_ref = ET.SubElement(p_prototype, if_dest_tag, {"DEST": "PORT-INTERFACE"})
                    if_ref.text = f"/PortInterfaces/{p_iface}"

            # Internal Behavior Skeleton
            ib_elem = ET.SubElement(comp_elem, "INTERNAL-BEHAVIORS")
            ib = ET.SubElement(ib_elem, "SWC-INTERNAL-BEHAVIOR")
            ET.SubElement(ib, "SHORT-NAME").text = f"IB_{c_name}"
            ET.SubElement(ib, "SUPPORTS-MULTIPLE-INSTANTIATION").text = "false"

            # Add Runnable
            runnables = ET.SubElement(ib, "RUNNABLES")
            runnable = ET.SubElement(runnables, "RUNNABLE-ENTITY")
            ET.SubElement(runnable, "SHORT-NAME").text = f"{c_name}_MainRunnable"
            ET.SubElement(runnable, "MINIMUM-START-INTERVAL").text = "0.01"
            ET.SubElement(runnable, "CAN-BE-INVOKED-CONCURRENTLY").text = "false"
            ET.SubElement(runnable, "SYMBOL").text = f"{c_name}_Step"

        # Pretty print XML string
        rough_string = ET.tostring(root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    @staticmethod
    def generate_mermaid_diagram(
        components: List[Dict[str, Any]],
        ports: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]]
    ) -> str:
        """
        Generate Mermaid.js flowchart diagram representing SWC architecture and connectors.
        """
        lines = [
            "```mermaid",
            "graph TB",
            "  %% AUTOSAR Software Component Architecture Diagram",
            "  classDef appSwc fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;",
            "  classDef bswSwc fill:#0f172a,stroke:#a855f7,stroke-width:2px,color:#f8fafc;",
            "  classDef sensorSwc fill:#1e1b4b,stroke:#22c55e,stroke-width:2px,color:#f8fafc;",
            "  classDef serviceSwc fill:#3b0764,stroke:#eab308,stroke-width:2px,color:#f8fafc;"
        ]

        # Add Component Nodes
        comp_names = set()
        for comp in components:
            name = comp.get("name", "").strip()
            if not name:
                continue
            comp_names.add(name)
            c_type = (comp.get("component_type") or "Application").lower()
            safe_id = name.replace(" ", "_").replace("-", "_")

            style_class = "appSwc"
            if "sensor" in c_type or "actuator" in c_type:
                style_class = "sensorSwc"
            elif "service" in c_type or "gateway" in c_type:
                style_class = "serviceSwc"
            elif "driver" in c_type or "mcal" in c_type:
                style_class = "bswSwc"

            label = f"<b>{name}</b><br/><i>[{comp.get('component_type', 'SWC')}]</i>"
            lines.append(f'  {safe_id}["{label}"]:::{style_class}')

        # Add Connections based on ports and dependencies
        connected_pairs = set()

        for dep in dependencies:
            src = dep.get("source_component", "").replace(" ", "_")
            tgt = dep.get("target_component", "").replace(" ", "_")
            if src and tgt and (src, tgt) not in connected_pairs:
                desc = dep.get("description", "RTE") or "RTE"
                desc = desc[:25] + "..." if len(desc) > 25 else desc
                lines.append(f'  {src} -->|"{desc}"| {tgt}')
                connected_pairs.add((src, tgt))

        # Match Provided ports to Required ports with same interface
        if_provided = {}
        if_required = {}
        for p in ports:
            if_name = p.get("interface_name")
            c_name = p.get("component_name", "").replace(" ", "_")
            p_type = (p.get("port_type") or "").lower()
            p_dir = (p.get("direction") or "").lower()

            if not if_name or not c_name:
                continue

            is_prov = "prov" in p_type or "out" in p_dir or "p-port" in p_type or "pport" in p_type
            if is_prov:
                if_provided.setdefault(if_name, []).append(c_name)
            else:
                if_required.setdefault(if_name, []).append(c_name)

        for if_name, providers in if_provided.items():
            if if_name in if_required:
                for p_comp in providers:
                    for r_comp in if_required[if_name]:
                        if p_comp != r_comp and (p_comp, r_comp) not in connected_pairs:
                            lines.append(f'  {p_comp} -.->|"{if_name}"| {r_comp}')
                            connected_pairs.add((p_comp, r_comp))

        lines.append("```")
        return "\n".join(lines)

    @staticmethod
    def export_json(data: Dict[str, Any]) -> str:
        """Export extracted data to formatted JSON string."""
        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def export_csv(items: List[Dict[str, Any]], fieldnames: Optional[List[str]] = None) -> str:
        """Export list of entity dicts to CSV string."""
        if not items:
            return ""
        output = io.StringIO()
        if not fieldnames:
            fieldnames = list(items[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for item in items:
            writer.writerow(item)
        return output.getvalue()
