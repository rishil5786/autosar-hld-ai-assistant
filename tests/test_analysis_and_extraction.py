"""
Unit and Integration Tests for AUTOSAR HLD AI Assistant
Tests entity extractors, inconsistency auditor, revision comparator, and ARXML export.
"""

import pytest
import xml.etree.ElementTree as ET

from app.extraction.component_extractor import extract_components
from app.extraction.interface_extractor import extract_interfaces
from app.extraction.port_extractor import extract_ports
from app.analysis.inconsistency_checker import InconsistencyChecker
from app.analysis.revision_comparator import RevisionComparator
from app.reports.export_service import ExportService
from app.analysis.traceability_matrix import TraceabilityEngine


def test_component_extraction():
    sample_text = """
    The Battery Management System includes:
    - CellVoltageMonitor: Measures analog cell voltages across 96 battery series cells.
    - ContactorControlManager: Controls main positive and negative contactors with precharge.
    - ThermalManagementService: Regulates coolant pump flow and refrigerant chiller valve.
    """
    comps = extract_components(sample_text, page_number=1)
    comp_names = [c["name"] for c in comps]

    assert "CellVoltageMonitor" in comp_names
    assert "ContactorControlManager" in comp_names
    assert "ThermalManagementService" in comp_names


def test_interface_extraction():
    sample_text = """
    3.1 Sender-Receiver Interfaces
    - If_CellVoltage: Transmits filtered cell voltage measurements.
    - If_CellTemperature: Transmits module temperatures.
    
    3.2 Client-Server Interfaces
    - If_ContactorCommand: RequestPrecharge(), OpenMainRelay().
    """
    interfaces = extract_interfaces(sample_text, page_number=2)
    if_names = [i["name"] for i in interfaces]

    assert any("CellVoltage" in name for name in if_names)
    assert any("ContactorCommand" in name or "CellTemperature" in name for name in if_names)


def test_inconsistency_checker_unconnected_port():
    checker = InconsistencyChecker()

    # Required port with NO provided port
    ports = [
        {"name": "R_CellVoltage", "port_type": "Required", "direction": "In", "interface_name": "If_CellVoltage", "component_name": "SOC_Estimator", "source_page": 1}
    ]
    interfaces = [{"name": "If_CellVoltage", "interface_type": "SenderReceiver"}]
    components = [{"name": "SOC_Estimator", "component_type": "Application"}]

    audit = checker.check_document("doc_test", components, interfaces, ports, [], [])
    
    # Should identify missing provider
    assert audit["total_findings"] > 0
    assert any(f["severity"] == "CRITICAL" for f in audit["findings"])
    assert any("Unconnected Port" in f["category"] or "Missing Provider" in f["category"] for f in audit["findings"])


def test_inconsistency_checker_layer_violation():
    checker = InconsistencyChecker()

    components = [
        {"name": "BatteryApplicationControl", "component_type": "Application"},
        {"name": "Can_Driver_Mcal", "component_type": "Driver"}
    ]
    dependencies = [
        {"source_component": "BatteryApplicationControl", "target_component": "Can_Driver_Mcal", "source_page": 1}
    ]

    audit = checker.check_document("doc_test", components, [], [], [], dependencies)
    assert any("Layer Violation" in f["category"] for f in audit["findings"])


def test_inconsistency_checker_cyclic_dependency():
    checker = InconsistencyChecker()

    dependencies = [
        {"source_component": "SWC_A", "target_component": "SWC_B"},
        {"source_component": "SWC_B", "target_component": "SWC_C"},
        {"source_component": "SWC_C", "target_component": "SWC_A"}
    ]

    audit = checker.check_document("doc_test", [], [], [], [], dependencies)
    assert any("Circular" in f["title"] or "Cyclic" in f["category"] for f in audit["findings"])


def test_revision_comparator():
    comparator = RevisionComparator()

    v1_data = {
        "version": "1.0",
        "components": [{"name": "CellVoltageMonitor", "component_type": "Sensor"}],
        "interfaces": [{"name": "If_CellVoltage", "interface_type": "SenderReceiver"}],
        "ports": [],
        "signals": [],
        "dependencies": []
    }

    v2_data = {
        "version": "2.0",
        "components": [
            {"name": "CellVoltageMonitor", "component_type": "Sensor"},
            {"name": "ActiveCellBalancingManager", "component_type": "Controller"}
        ],
        "interfaces": [{"name": "If_CellVoltage", "interface_type": "SenderReceiver"}],
        "ports": [],
        "signals": [],
        "dependencies": []
    }

    diff = comparator.compare_documents(v1_data, v2_data)
    assert len(diff["components"]["added"]) == 1
    assert diff["components"]["added"][0]["name"] == "ActiveCellBalancingManager"


def test_arxml_generation():
    components = [{"name": "CellVoltageMonitor", "component_type": "Sensor"}]
    interfaces = [{"name": "If_CellVoltage", "interface_type": "SenderReceiver"}]
    ports = [{"name": "P_CellVoltage", "port_type": "Provided", "interface_name": "If_CellVoltage", "component_name": "CellVoltageMonitor"}]

    arxml_str = ExportService.generate_arxml(components, interfaces, ports, project_name="TestBMS")

    # Validate valid XML structure
    root = ET.fromstring(arxml_str)
    assert root.tag == "{http://autosar.org/schema/r4.0}AUTOSAR" or root.tag == "AUTOSAR"
    assert "CellVoltageMonitor" in arxml_str
    assert "If_CellVoltage" in arxml_str
