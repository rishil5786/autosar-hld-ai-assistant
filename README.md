# ⚡ AUTOSAR HLD AI Document Analysis Assistant

An end-to-end, evidence-grounded AI-powered architecture assistant for **AUTOSAR High-Level Design (HLD)** document ingestion, entity extraction, semantic RAG Q&A with citations, revision diffing, compliance and inconsistency auditing, and ARXML export.

Based on **Case Study 1: AUTOSAR HLD Document Analysis Assistant** from the Automotive Engineering AI Project Reference.

---

## 🚀 Key Functional Capabilities

1. **📄 Document Ingestion Hub**:
   - Parses multi-page AUTOSAR HLD PDFs using PyMuPDF and pdfplumber.
   - Context-aware section and heading chunking.
   - Vector embeddings with BGE / E5 models and persistent FAISS indexing.
   - Automatic metadata and table extraction.

2. **💬 Evidence-Grounded Architecture RAG Q&A**:
   - Multi-turn question answering on complex SWC behaviors, contactor states, cell monitoring, and timing loops.
   - Structured citations with exact page numbers, section titles, relevance scores, and source text snippets.
   - Support for multiple LLM providers (Local Ollama, OpenAI GPT-4o, Anthropic Claude, Groq Llama-3, and rule-based offline fallback).

3. **🧩 Architecture Entity Extraction & Catalog**:
   - Software Components (SensorActuatorSWC, ApplicationSWC, ServiceSWC, BSW Drivers).
   - Port Interfaces (Sender-Receiver, Client-Server, Parameter).
   - Provided (PPort) & Required (RPort) Ports with directionality and mapped interfaces.
   - Signals and Inter-Component Dependencies.

4. **🔄 Revision Comparison & Diff Engine**:
   - Compares Baseline (e.g. V1.0) against Target (e.g. V2.0) HLD revisions.
   - Flags breaking architectural changes (component deletions, interface signature changes, dangling connectors).
   - Detailed component-level and interface-level delta metrics.

5. **⚠️ Architecture Compliance & Inconsistency Auditor**:
   - Detects unconnected / unconsumed ports (missing providers or consumers).
   - Identifies undefined interface references.
   - Flags AUTOSAR layer boundary violations (e.g., Application SWC bypassing RTE/BSW to call low-level MCAL directly).
   - Detects cyclic component dependencies that violate RTE initialization order.
   - Calculates overall Architecture Health Score (0 - 100).

6. **📊 Bidirectional Traceability Matrix**:
   - Extracts functional requirements (`REQ_...`, shall/must statements) and maps them to implementing SWCs, ports, and interfaces.
   - Computes requirement coverage and component implementation metrics.

7. **🕸️ Interactive Component Network Visualization**:
   - Dynamic Mermaid.js flowcharts rendering SWCs, ports, and data flow pipelines in real time.

8. **📑 Formal Engineering Reports & Model Export**:
   - Generates formal Markdown & HTML Architecture Summary and Diff reports.
   - Generates AUTOSAR 4.x compliant **ARXML** XML skeletons.
   - Exports structured datasets in JSON and CSV formats.

---

## 🛠️ Technology Stack

- **User Interface**: Streamlit (Modern dark automotive UI with glassmorphism & responsive badges)
- **API Backend**: FastAPI with Uvicorn
- **Embeddings**: `sentence-transformers` (`BAAI/bge-small-en-v1.5`)
- **Vector Database**: FAISS (Facebook AI Similarity Search)
- **Database**: SQLite with SQLAlchemy ORM
- **PDF Extraction**: PyMuPDF (`fitz`), pdfplumber, Tesseract OCR
- **Visualization**: Plotly, Mermaid.js

---

## ⚡ Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Generate Sample HLD Documents & Seed Database
```bash
python data/generate_sample_hld_pdfs.py
python data/seed_data.py
```

### 3. Launch the Streamlit Engineering Dashboard
```bash
python run.py --mode frontend --port 8501
```
Open your browser at [http://localhost:8501](http://localhost:8501).

### 4. (Optional) Launch the FastAPI REST API
```bash
python run.py --mode backend --port 8000
```
API documentation available at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## 🧪 Running Unit & Integration Tests
```bash
python -m pytest tests/test_analysis_and_extraction.py -v
```

---

## 🔒 Governance & ASPICE / ISO 26262 Notice
AI-extracted architecture entities, dependency maps, and compliance audit reports are designed to assist automotive systems engineers and must be formally verified and approved by an authorized AUTOSAR Architect before software release or safety certification.
