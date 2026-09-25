"""
Generate sample AUTOSAR HLD PDF documents for testing and immediate demonstration.
"""

import os
import fitz  # PyMuPDF


def create_sample_hld_v1(output_path: str):
    doc = fitz.open()

    # Page 1: Title & Overview
    page1 = doc.new_page()
    text_p1 = """
================================================================================
AUTOSAR HIGH-LEVEL DESIGN SPECIFICATION (HLD)
Document ID: HLD-BMS-2026-V1.0
System: Electric Vehicle Battery Management System (BMS)
Version: 1.0 (Baseline Architecture)
Classification: ASIL-C / ASIL-D
================================================================================

1. System Architectural Overview
The Battery Management System (BMS) Software Architecture is designed in compliance with AUTOSAR 4.3 Classic Platform standards.
The BMS ECU monitors battery cells, executes state of charge (SOC) algorithms, manages high-voltage contactors, controls thermal loops, and enforces safety limits.

Primary Requirements:
- REQ_BMS_001: The system shall monitor all individual battery cell voltages with an update rate of 50ms.
- REQ_BMS_002: The system shall monitor cell temperatures and trigger cooling when temp exceeds 45°C.
- REQ_BMS_003: The system shall calculate Battery State of Charge (SOC) and State of Health (SOH).
- REQ_BMS_004: The contactor control manager shall open HV contactors upon critical over-current or isolation fault.
- REQ_BMS_005: Thermal management service shall regulate coolant pump flow based on temperature gradients.

2. Software Components (SWC) Definition
The application layer comprises the following core AUTOSAR Software Components:

- CellVoltageMonitor (SensorActuatorSWC):
  Acquires cell voltages via ADC / SPI abstraction, performs low-pass filtering, and publishes cell voltage arrays.
  
- CellTemperatureMonitor (SensorActuatorSWC):
  Reads NTC thermistor sensor arrays across battery modules, detects temperature hot spots.

- SOC_SOE_Estimator (ApplicationSWC):
  Executes Extended Kalman Filter (EKF) algorithms to estimate State of Charge (SOC), State of Energy (SOE), and available power limits.

- ContactorControlManager (ApplicationSWC):
  Implements the high-voltage precharge sequence, main contactor closing/opening logic, and emergency pyrofuse activation.

- ThermalManagementService (ServiceSWC):
  Computes required cooling/heating thermal power and commands the chiller and coolant pump actuators.
"""
    page1.insert_text((50, 50), text_p1, fontsize=9.5)

    # Page 2: Interfaces and Ports
    page2 = doc.new_page()
    text_p2 = """
================================================================================
AUTOSAR HLD SPECIFICATION: BMS Architecture (Page 2)
================================================================================

3. Port Interfaces Specification

3.1 Sender-Receiver Interfaces
- If_CellVoltage:
  Carries filtered cell voltage data elements [Array of uint16, mV].
  Related Component: CellVoltageMonitor.

- If_CellTemperature:
  Carries module temperature readings [Array of sint16, 0.1 deg C].
  Related Component: CellTemperatureMonitor.

- If_BatteryStateOfCharge:
  Carries calculated SOC percentage [uint16, 0.01% resolution] and SOE [kWh].
  Related Component: SOC_SOE_Estimator.

- If_ThermalCommand:
  Transmits cooling pump RPM and chiller valve position targets.
  Related Component: ThermalManagementService.

3.2 Client-Server Interfaces
- If_ContactorCommand:
  Operations: RequestPrecharge(), OpenMainRelay(), EmergencyShutdown().
  Related Component: ContactorControlManager.

4. Component Port Allocations
- CellVoltageMonitor:
  - Port P_CellVoltage: Provided Port (PPort), Interface: If_CellVoltage
  
- CellTemperatureMonitor:
  - Port P_CellTemp: Provided Port (PPort), Interface: If_CellTemperature

- SOC_SOE_Estimator:
  - Port R_CellVoltage: Required Port (RPort), Interface: If_CellVoltage
  - Port R_CellTemp: Required Port (RPort), Interface: If_CellTemperature
  - Port P_BatteryStateOfCharge: Provided Port (PPort), Interface: If_BatteryStateOfCharge

- ContactorControlManager:
  - Port R_BatterySOC: Required Port (RPort), Interface: If_BatteryStateOfCharge
  - Port P_ContactorControl: Provided Port (PPort), Interface: If_ContactorCommand

- ThermalManagementService:
  - Port R_CellTemp: Required Port (RPort), Interface: If_CellTemperature
  - Port P_ThermalCmd: Provided Port (PPort), Interface: If_ThermalCommand
"""
    page2.insert_text((50, 50), text_p2, fontsize=9.5)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    doc.close()
    print(f"Generated sample HLD v1.0: {output_path}")


def create_sample_hld_v2(output_path: str):
    doc = fitz.open()

    # Page 1: Title & Overview
    page1 = doc.new_page()
    text_p1 = """
================================================================================
AUTOSAR HIGH-LEVEL DESIGN SPECIFICATION (HLD)
Document ID: HLD-BMS-2026-V2.0
System: Electric Vehicle Battery Management System (BMS) - Fast Charging Upgrade
Version: 2.0 (Updated Architecture)
Classification: ASIL-D
================================================================================

1. System Architectural Overview
Version 2.0 introduces ultra-fast DC charging support (800V architecture), active cell balancing control, and cybersecurity authentication gateway integration.

Updated Requirements:
- REQ_BMS_001: The system shall monitor all individual battery cell voltages with an update rate of 50ms.
- REQ_BMS_002: The system shall monitor cell temperatures and trigger cooling when temp exceeds 45°C.
- REQ_BMS_003: The system shall calculate Battery State of Charge (SOC) and State of Health (SOH).
- REQ_BMS_004: The contactor control manager shall open HV contactors upon critical over-current or isolation fault.
- REQ_BMS_005: Thermal management service shall regulate coolant pump flow based on temperature gradients.
- REQ_BMS_006: The system shall execute active cell balancing algorithms during DC fast charging.
- REQ_BMS_007: IsolationMonitor shall continuously evaluate high-voltage chassis insulation resistance.

2. Software Components (SWC) Definition
- CellVoltageMonitor (SensorActuatorSWC):
  Acquires cell voltages via ADC / SPI abstraction and publishes cell voltage arrays.

- CellTemperatureMonitor (SensorActuatorSWC):
  Reads NTC thermistor sensor arrays across battery modules.

- SOC_SOE_Estimator (ApplicationSWC):
  Enhanced multi-model observer estimating SOC, SOH, and maximum fast-charge pulse power.

- ContactorControlManager (ApplicationSWC):
  Handles 800V DC fast charge contactor sequencing, AC charging interlocks, and emergency disconnects.

- ThermalManagementService (ServiceSWC):
  Advanced chiller regulation supporting rapid pre-conditioning for high-power DC fast charging.

- ActiveCellBalancingManager (ApplicationSWC): [NEW in V2.0]
  Controls bi-directional flyback active balancing circuits to equalize cell voltages dynamically.

- IsolationMonitor (SensorActuatorSWC): [NEW in V2.0]
  Continuously measures positive and negative rail isolation impedance to chassis ground.
"""
    page1.insert_text((50, 50), text_p1, fontsize=9.5)

    # Page 2: Interfaces and Ports
    page2 = doc.new_page()
    text_p2 = """
================================================================================
AUTOSAR HLD SPECIFICATION: BMS Architecture (Page 2 - V2.0)
================================================================================

3. Port Interfaces Specification

3.1 Sender-Receiver Interfaces
- If_CellVoltage:
  Carries filtered cell voltage data elements [Array of uint16, mV].
  Related Component: CellVoltageMonitor.

- If_CellTemperature:
  Carries module temperature readings [Array of sint16, 0.1 deg C].
  Related Component: CellTemperatureMonitor.

- If_BatteryStateOfCharge:
  Carries calculated SOC percentage and available charge/discharge power limits.
  Related Component: SOC_SOE_Estimator.

- If_ThermalCommand:
  Transmits cooling pump RPM and chiller valve targets.
  Related Component: ThermalManagementService.

- If_CellBalancingCommand: [NEW in V2.0]
  Carries PWM target duty cycle and target cell IDs for active balancing.
  Related Component: ActiveCellBalancingManager.

- If_IsolationStatus: [NEW in V2.0]
  Carries measured isolation resistance in kOhms and fault flag.
  Related Component: IsolationMonitor.

3.2 Client-Server Interfaces
- If_ContactorCommand:
  Operations: RequestPrecharge(), OpenMainRelay(), EmergencyShutdown(), FastChargeConnect().
  Related Component: ContactorControlManager.

4. Component Port Allocations
- ActiveCellBalancingManager:
  - Port R_CellVoltage: Required Port (RPort), Interface: If_CellVoltage
  - Port P_BalancingCmd: Provided Port (PPort), Interface: If_CellBalancingCommand

- IsolationMonitor:
  - Port P_IsolationState: Provided Port (PPort), Interface: If_IsolationStatus

- ContactorControlManager:
  - Port R_BatterySOC: Required Port (RPort), Interface: If_BatteryStateOfCharge
  - Port R_IsolationCheck: Required Port (RPort), Interface: If_IsolationStatus
  - Port P_ContactorControl: Provided Port (PPort), Interface: If_ContactorCommand
"""
    page2.insert_text((50, 50), text_p2, fontsize=9.5)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    doc.close()
    print(f"Generated sample HLD v2.0: {output_path}")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sample_dir = os.path.join(base_dir, "sample_documents")
    create_sample_hld_v1(os.path.join(sample_dir, "BMS_HLD_Specification_v1.0.pdf"))
    create_sample_hld_v2(os.path.join(sample_dir, "BMS_HLD_Specification_v2.0.pdf"))
