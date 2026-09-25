"""
AUTOSAR HLD AI - Engineering Dashboard & Analysis Assistant
Streamlit-based engineering web application providing interactive tools for
HLD document ingestion, RAG Q&A with citations, entity exploration, revision diffing,
inconsistency auditing, traceability, and ARXML/Report exports.
"""

import os
import sys
import json
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Set page config
st.set_page_config(
    page_title="AUTOSAR HLD AI Assistant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (CSS)
st.markdown("""
<style>
    /* Modern Automotive AI Theme */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0369a1 100%);
        padding: 24px 32px;
        border-radius: 16px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(56, 189, 248, 0.2);
    }
    
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-critical { background-color: #ef4444; color: white; }
    .badge-high { background-color: #f97316; color: white; }
    .badge-warning { background-color: #eab308; color: black; }
    .badge-info { background-color: #3b82f6; color: white; }
    .badge-success { background-color: #22c55e; color: white; }

    .stat-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .stat-card:hover {
        transform: translateY(-2px);
        border-color: #38bdf8;
    }
    .stat-val {
        font-size: 2rem;
        font-weight: 700;
        color: #38bdf8;
    }
    .stat-lbl {
        font-size: 0.85rem;
        color: #94a3b8;
        margin-top: 4px;
    }

    .citation-card {
        background-color: #0f172a;
        border-left: 4px solid #38bdf8;
        padding: 12px 16px;
        margin-top: 10px;
        margin-bottom: 10px;
        border-radius: 0 8px 8px 0;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Add parent path to import backend modules
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.utils.config import settings
from app.backend.database import init_db, get_db_session
from app.backend.models import Document, Project, Chunk, Component, Interface, Port, Signal, Dependency
from app.ingestion.pdf_parser import parse_pdf
from app.ingestion.chunker import chunk_document
from app.embeddings.embedding_service import get_embedding_service
from app.vectorstore.faiss_store import get_faiss_store
from app.rag.rag_pipeline import run_rag_query
from app.extraction.component_extractor import extract_components
from app.extraction.interface_extractor import extract_interfaces
from app.extraction.port_extractor import extract_ports
from app.analysis.revision_comparator import RevisionComparator
from app.analysis.inconsistency_checker import InconsistencyChecker
from app.analysis.traceability_matrix import TraceabilityEngine
from app.reports.export_service import ExportService
from app.reports.report_generator import ReportGenerator

# Ensure DB initialized
init_db()


# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/car.png", width=64)
    st.title("AUTOSAR HLD AI")
    st.caption("Document Analysis & Validation Assistant")
    st.markdown("---")

    nav_choice = st.radio(
        "Navigation",
        [
            "📁 Document Ingestion",
            "💬 RAG Q&A Assistant",
            "🧩 Architecture Entities",
            "🔄 Revision Comparison",
            "⚠️ Compliance & Inconsistencies",
            "📊 Traceability Matrix",
            "🕸️ Interactive Architecture",
            "📑 Report & Export Center"
        ],
        index=0
    )

    st.markdown("---")
    st.subheader("⚙️ System Configuration")
    llm_provider = st.selectbox("LLM Provider", ["Local / Ollama", "OpenAI (GPT-4o)", "Anthropic (Claude)", "Groq (Llama-3)", "Built-in Extractor / Fallback"], index=4)
    st.caption("Target AUTOSAR Standard: **AUTOSAR 4.3 / 4.4 Classic**")

    # Global Stats
    with get_db_session() as db:
        doc_count = db.query(Document).count()
        comp_count = db.query(Component).count()
        port_count = db.query(Port).count()

    st.markdown("---")
    st.caption(f"📊 Active Docs: **{doc_count}** | SWCs: **{comp_count}** | Ports: **{port_count}**")


# ---------------- HEADER ----------------
st.markdown("""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="margin: 0; font-size: 1.8rem; font-weight: 800;">⚡ AUTOSAR HLD Document Analysis Assistant</h1>
            <p style="margin: 4px 0 0 0; opacity: 0.85; font-size: 0.95rem;">Automotive AI Reference Solution · High-Level Design Ingestion, Evidence-Grounded RAG, Entity Traceability & Audit</p>
        </div>
        <div>
            <span class="badge badge-success">ASIL-D Ready</span>
            <span class="badge badge-info">AUTOSAR Classic & Adaptive</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ---------------- TAB 1: DOCUMENT INGESTION ----------------
if nav_choice == "📁 Document Ingestion":
    st.header("📁 Document Ingestion & Knowledge Base")
    st.write("Upload AUTOSAR High-Level Design (HLD) specifications to parse, chunk, create embeddings, and extract architecture structures.")

    col1, col2 = st.columns([1.5, 1])

    with col1:
        uploaded_file = st.file_uploader("Upload AUTOSAR HLD PDF Document", type=["pdf"], help="Upload an architectural HLD PDF file.")
        version_input = st.text_input("Document Version Label", value="1.0", help="Version tag (e.g., 1.0, 2.1-RC)")

        if uploaded_file is not None and st.button("🚀 Process & Ingest Document", type="primary"):
            with st.spinner("Processing PDF: Parsing, OCR, Chunking, Generating Embeddings & Extracting Entities..."):
                import uuid
                doc_id = f"doc_{uuid.uuid4().hex[:10]}"
                os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
                file_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}_{uploaded_file.name}")

                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                with get_db_session() as db:
                    project = db.query(Project).first()
                    if not project:
                        project = Project(id=1, name="Default AUTOSAR Project", owner_id=1)
                        db.add(project)
                        db.commit()

                    db_doc = Document(
                        document_id=doc_id,
                        project_id=project.id,
                        filename=os.path.basename(file_path),
                        original_filename=uploaded_file.name,
                        file_hash=doc_id,
                        file_size=len(uploaded_file.getbuffer()),
                        version=version_input,
                        status="processing"
                    )
                    db.add(db_doc)
                    db.commit()

                    # 1. Parse PDF
                    parsed = parse_pdf(file_path, filename=uploaded_file.name)
                    db_doc.page_count = parsed.page_count

                    # 2. Chunk
                    chunks = chunk_document(parsed, document_id=doc_id)
                    chunk_texts = []
                    chunk_metas = []
                    for ch in chunks:
                        db.add(Chunk(
                            chunk_id=ch.chunk_id,
                            document_id=doc_id,
                            document_name=uploaded_file.name,
                            page_number=ch.page_number,
                            section=ch.section,
                            text=ch.text,
                            chunk_index=ch.chunk_index,
                            token_count=ch.token_count,
                            metadata_json=ch.metadata
                        ))
                        chunk_texts.append(ch.text)
                        chunk_metas.append(ch.metadata)

                    # 3. Embed & Vector Store
                    embedding_svc = get_embedding_service()
                    vstore = get_faiss_store()
                    if chunk_texts:
                        embeddings = embedding_svc.embed_texts(chunk_texts)
                        if embeddings is not None:
                            vstore.add_vectors(embeddings, chunk_texts, chunk_metas)
                            vstore.save()

                    # 4. Extract Entities
                    total_comps, total_ifs, total_ports = 0, 0, 0
                    for page in parsed.pages:
                        p_num = page.page_number
                        p_text = page.text
                        for c in extract_components(p_text, page_number=p_num):
                            db.add(Component(
                                document_id=doc_id,
                                name=c["name"],
                                description=c.get("description", ""),
                                component_type=c.get("component_type", "Component"),
                                source_page=p_num,
                                confidence=c.get("confidence", 0.8)
                            ))
                            total_comps += 1

                        for i in extract_interfaces(p_text, page_number=p_num):
                            db.add(Interface(
                                document_id=doc_id,
                                name=i["name"],
                                interface_type=i.get("interface_type", "SenderReceiver"),
                                description=i.get("description", ""),
                                related_component=i.get("related_component", ""),
                                source_page=p_num,
                                confidence=i.get("confidence", 0.8)
                            ))
                            total_ifs += 1

                        for p in extract_ports(p_text, page_number=p_num):
                            db.add(Port(
                                document_id=doc_id,
                                name=p["name"],
                                port_type=p.get("port_type", "Provided"),
                                direction=p.get("direction", "Out"),
                                interface_name=p.get("interface_name", ""),
                                component_name=p.get("component_name", ""),
                                source_page=p_num,
                                confidence=p.get("confidence", 0.8)
                            ))
                            total_ports += 1

                    db_doc.status = "processed"
                    db.commit()

                st.success(f"✅ Document successfully ingested! Extracted {total_comps} SWCs, {total_ifs} Interfaces, {total_ports} Ports across {len(chunks)} searchable chunks.")
                st.rerun()

    with col2:
        st.subheader("📚 Ingested Documents Repository")
        with get_db_session() as db:
            docs = db.query(Document).order_by(Document.created_at.desc()).all()
            if not docs:
                st.info("No documents uploaded yet. Upload a PDF or load a sample document.")
            else:
                for d in docs:
                    with st.expander(f"📄 {d.original_filename} (v{d.version or '1.0'})", expanded=True):
                        st.write(f"**Document ID:** `{d.document_id}`")
                        st.write(f"**Pages:** {d.page_count} | **Status:** `{d.status}`")
                        st.write(f"**Size:** {round(d.file_size/1024, 1)} KB | **Created:** {d.created_at.strftime('%Y-%m-%d %H:%M')}")


# ---------------- TAB 2: RAG Q&A ----------------
elif nav_choice == "💬 RAG Q&A Assistant":
    st.header("💬 Evidence-Grounded Architecture RAG Q&A")
    st.write("Ask architectural, interface, dependency, and timing questions. Every response includes page citations and grounded evidence.")

    with get_db_session() as db:
        docs = db.query(Document).all()
        doc_options = {"All Documents (Global Search)": None}
        for d in docs:
            doc_options[f"{d.original_filename} (v{d.version or '1.0'})"] = d.document_id

    c1, c2 = st.columns([2, 1])
    with c1:
        selected_doc_label = st.selectbox("Search Scope", list(doc_options.keys()))
        selected_doc_id = doc_options[selected_doc_label]
    with c2:
        top_k = st.slider("Retrieved Context Chunks (Top-K)", min_value=2, max_value=8, value=4)

    # Sample Quick Questions
    st.markdown("##### 💡 Suggested Architecture Queries:")
    quick_cols = st.columns(3)
    sample_queries = [
        "What are the main SWCs and their responsibilities?",
        "Which interfaces are used for cell temperature and voltage monitoring?",
        "Explain the contactor control state machine and safety interlocks."
    ]
    user_query = ""
    for i, q in enumerate(sample_queries):
        if quick_cols[i].button(f"🔍 {q[:32]}...", key=f"quick_{i}"):
            user_query = q

    query_input = st.text_input("Enter your architectural query:", value=user_query, placeholder="e.g., Which component provides the battery state of charge (SOC) interface?")

    if st.button("🚀 Run Grounded Search", type="primary") or query_input:
        if query_input:
            with st.spinner("Retrieving semantic evidence from FAISS & generating cited answer..."):
                result = run_rag_query(question=query_input, document_id=selected_doc_id, top_k=top_k)

                st.markdown("### 🤖 Answer")
                st.markdown(result.answer or "No answer generated.")

                citations = result.citations or []
                if citations:
                    st.markdown("#### 📚 Verified Source Evidence & Citations")
                    for idx, cit in enumerate(citations):
                        with st.container():
                            st.markdown(f"""
                            <div class="citation-card">
                                <b>Citation [{idx+1}]</b> — <b>Document:</b> {cit.document_name} | <b>Page:</b> {cit.page_number} | <b>Relevance Score:</b> {round(cit.relevance_score*100, 1)}%<br/>
                                <span style="color: #cbd5e1; font-style: italic;">"{cit.text_excerpt}"</span>
                            </div>
                            """, unsafe_allow_html=True)

                with st.expander("🔍 View Raw Retrieved Chunks & Vector Similarity"):
                    for ch in result.retrieved_chunks or []:
                        st.json(ch.model_dump() if hasattr(ch, "model_dump") else ch.__dict__)


# ---------------- TAB 3: ENTITIES ----------------
elif nav_choice == "🧩 Architecture Entities":
    st.header("🧩 Extracted AUTOSAR Architecture Inventory")
    st.write("Browse and inspect extracted Software Components, Interfaces, Ports, Signals, and Inter-Component Dependencies.")

    with get_db_session() as db:
        docs = db.query(Document).all()
        if not docs:
            st.warning("No documents available in the database. Please ingest an HLD document first.")
        else:
            doc_map = {f"{d.original_filename} (v{d.version or '1.0'})": d.document_id for d in docs}
            selected_doc = st.selectbox("Select Architecture Specification", list(doc_map.keys()))
            curr_doc_id = doc_map[selected_doc]

            comps = db.query(Component).filter(Component.document_id == curr_doc_id).all()
            ifs = db.query(Interface).filter(Interface.document_id == curr_doc_id).all()
            ports = db.query(Port).filter(Port.document_id == curr_doc_id).all()
            sigs = db.query(Signal).filter(Signal.document_id == curr_doc_id).all()

            # Metric Cards
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f'<div class="stat-card"><div class="stat-val">{len(comps)}</div><div class="stat-lbl">Software Components</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="stat-card"><div class="stat-val">{len(ifs)}</div><div class="stat-lbl">Port Interfaces</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="stat-card"><div class="stat-val">{len(ports)}</div><div class="stat-lbl">Allocated Ports</div></div>', unsafe_allow_html=True)
            m4.markdown(f'<div class="stat-card"><div class="stat-val">{len(sigs)}</div><div class="stat-lbl">Signals / Data</div></div>', unsafe_allow_html=True)

            st.write("")
            entity_subtab = st.tabs(["📦 Software Components (SWCs)", "🔌 Interfaces", "📍 Ports", "📡 Signals"])

            with entity_subtab[0]:
                if comps:
                    comp_df = pd.DataFrame([{
                        "Component Name": c.name,
                        "Type": c.component_type,
                        "Source Page": c.source_page,
                        "Confidence": f"{round((c.confidence or 1.0)*100)}%",
                        "Description": c.description
                    } for c in comps])
                    st.dataframe(comp_df, use_container_width=True)
                else:
                    st.info("No SWCs extracted for this document.")

            with entity_subtab[1]:
                if ifs:
                    if_df = pd.DataFrame([{
                        "Interface Name": i.name,
                        "Type": i.interface_type,
                        "Related Component": i.related_component,
                        "Source Page": i.source_page,
                        "Description": i.description
                    } for i in ifs])
                    st.dataframe(if_df, use_container_width=True)
                else:
                    st.info("No interfaces extracted.")

            with entity_subtab[2]:
                if ports:
                    port_df = pd.DataFrame([{
                        "Port Name": p.name,
                        "Component": p.component_name,
                        "Port Type": p.port_type,
                        "Direction": p.direction,
                        "Mapped Interface": p.interface_name,
                        "Source Page": p.source_page
                    } for p in ports])
                    st.dataframe(port_df, use_container_width=True)
                else:
                    st.info("No ports extracted.")

            with entity_subtab[3]:
                if sigs:
                    sig_df = pd.DataFrame([{
                        "Signal Name": s.name,
                        "Type": s.signal_type,
                        "Source": s.source_component,
                        "Target": s.target_component,
                        "Source Page": s.source_page
                    } for s in sigs])
                    st.dataframe(sig_df, use_container_width=True)
                else:
                    st.info("No signals found.")


# ---------------- TAB 4: REVISION COMPARISON ----------------
elif nav_choice == "🔄 Revision Comparison":
    st.header("🔄 Document Revision Comparison & Impact Analysis")
    st.write("Compare two document revisions (e.g. Baseline V1.0 vs Target V2.0) to highlight added, removed, or modified components, interfaces, and breaking changes.")

    with get_db_session() as db:
        docs = db.query(Document).all()
        if len(docs) < 2:
            st.info("At least two ingested documents are required for comparison. Upload a second revision in the Document Ingestion tab or use sample documents.")
        else:
            doc_dict = {f"{d.original_filename} (v{d.version or '1.0'})": d for d in docs}
            c1, c2 = st.columns(2)
            with c1:
                v1_key = st.selectbox("Baseline Revision (V1)", list(doc_dict.keys()), index=0)
            with c2:
                v2_key = st.selectbox("Target Revision (V2)", list(doc_dict.keys()), index=1 if len(doc_dict) > 1 else 0)

            if st.button("🚀 Run Architectural Comparison Diff", type="primary"):
                d1 = doc_dict[v1_key]
                d2 = doc_dict[v2_key]

                def get_doc_payload(d):
                    return {
                        "document_id": d.document_id,
                        "filename": d.original_filename,
                        "version": d.version or "1.0",
                        "components": [c.__dict__ for c in db.query(Component).filter(Component.document_id == d.document_id).all()],
                        "interfaces": [i.__dict__ for i in db.query(Interface).filter(Interface.document_id == d.document_id).all()],
                        "ports": [p.__dict__ for p in db.query(Port).filter(Port.document_id == d.document_id).all()],
                        "signals": [s.__dict__ for s in db.query(Signal).filter(Signal.document_id == d.document_id).all()],
                        "dependencies": [dep.__dict__ for dep in db.query(Dependency).filter(Dependency.document_id == d.document_id).all()],
                    }

                comparator = RevisionComparator()
                diff = comparator.compare_documents(get_doc_payload(d1), get_doc_payload(d2))

                st.subheader("📋 Evolution Summary")
                st.info(diff.get("evolution_summary", ""))

                m1, m2, m3 = st.columns(3)
                m1.metric("Total Architectural Changes", diff.get("total_changes_count", 0))
                m2.metric("Breaking Changes Identified", diff.get("breaking_changes_count", 0), delta_color="inverse")
                m3.metric("Components Delta", f"+{len(diff['components']['added'])} / -{len(diff['components']['removed'])}")

                # Breaking Changes Table
                if diff.get("breaking_changes"):
                    st.markdown("### ⚠️ Breaking Changes & Risk Assessment")
                    b_df = pd.DataFrame(diff["breaking_changes"])
                    st.dataframe(b_df, use_container_width=True)

                # Component Changes
                st.markdown("### 📦 Component Level Diff")
                c_tabs = st.tabs(["Introduced (+) ", "Decommissioned (-) ", "Modified (Δ)"])
                with c_tabs[0]:
                    if diff["components"]["added"]:
                        st.dataframe(pd.DataFrame(diff["components"]["added"]), use_container_width=True)
                    else:
                        st.write("No components added.")
                with c_tabs[1]:
                    if diff["components"]["removed"]:
                        st.dataframe(pd.DataFrame(diff["components"]["removed"]), use_container_width=True)
                    else:
                        st.write("No components removed.")
                with c_tabs[2]:
                    if diff["components"]["modified"]:
                        st.json(diff["components"]["modified"])
                    else:
                        st.write("No components modified.")


# ---------------- TAB 5: INCONSISTENCIES ----------------
elif nav_choice == "⚠️ Compliance & Inconsistencies":
    st.header("⚠️ AUTOSAR Architecture Compliance & Inconsistency Auditor")
    st.write("Automated rule-based checks for unconnected ports, missing interface definitions, layer violations, orphaned SWCs, and naming anomalies.")

    with get_db_session() as db:
        docs = db.query(Document).all()
        if not docs:
            st.warning("No documents available.")
        else:
            doc_map = {f"{d.original_filename} (v{d.version or '1.0'})": d.document_id for d in docs}
            selected_doc = st.selectbox("Select Document for Audit", list(doc_map.keys()))
            curr_doc_id = doc_map[selected_doc]

            if st.button("🚀 Run Architecture Audit Scanner", type="primary"):
                comps = [c.__dict__ for c in db.query(Component).filter(Component.document_id == curr_doc_id).all()]
                ifs = [i.__dict__ for i in db.query(Interface).filter(Interface.document_id == curr_doc_id).all()]
                ports = [p.__dict__ for p in db.query(Port).filter(Port.document_id == curr_doc_id).all()]
                sigs = [s.__dict__ for s in db.query(Signal).filter(Signal.document_id == curr_doc_id).all()]
                deps = [d.__dict__ for d in db.query(Dependency).filter(Dependency.document_id == curr_doc_id).all()]

                checker = InconsistencyChecker()
                audit = checker.check_document(curr_doc_id, comps, ifs, ports, sigs, deps)

                # Health Score Gauge
                col1, col2 = st.columns([1, 2])
                with col1:
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=audit.get("health_score", 100),
                        title={'text': "Architecture Health Score"},
                        gauge={
                            'axis': {'range': [0, 100]},
                            'bar': {'color': "#38bdf8"},
                            'steps': [
                                {'range': [0, 50], 'color': "#7f1d1d"},
                                {'range': [50, 80], 'color': "#78350f"},
                                {'range': [80, 100], 'color': "#064e3b"}
                            ],
                        }
                    ))
                    fig.update_layout(height=260, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', font=dict(color="white"))
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    st.markdown("#### Audit Severity Breakdown")
                    st.markdown(f"- 🔴 **Critical Mismatches:** `{audit.get('critical_count', 0)}`")
                    st.markdown(f"- 🟠 **High Risk Findings:** `{audit.get('high_count', 0)}`")
                    st.markdown(f"- 🟡 **Warnings:** `{audit.get('warning_count', 0)}`")
                    st.markdown(f"- 🔵 **Best Practice Notes:** `{audit.get('info_count', 0)}`")

                st.markdown("### 📋 Audit Findings & Recommended Remediations")
                findings = audit.get("findings", [])
                if not findings:
                    st.success("🎉 No architectural inconsistencies or layer violations detected!")
                else:
                    for f in findings:
                        sev = f.get("severity", "INFO")
                        badge_class = f"badge-{sev.lower()}"
                        with st.expander(f"[{sev}] {f.get('title')}", expanded=(sev == "CRITICAL")):
                            st.markdown(f"**Category:** `{f.get('category')}`")
                            st.write(f.get("description"))
                            st.markdown(f"**💡 Recommended Action:** `{f.get('recommendation')}`")
                            if f.get("source_page"):
                                st.caption(f"Source Reference: Page {f.get('source_page')}")


# ---------------- TAB 6: TRACEABILITY MATRIX ----------------
elif nav_choice == "📊 Traceability Matrix":
    st.header("📊 Requirement-to-Architecture Traceability Matrix")
    st.write("Verify bidirectional traceability between functional requirements (shall/must statements) and implementing AUTOSAR SWCs, interfaces, and ports.")

    with get_db_session() as db:
        docs = db.query(Document).all()
        if not docs:
            st.warning("No documents available.")
        else:
            doc_map = {f"{d.original_filename} (v{d.version or '1.0'})": d.document_id for d in docs}
            selected_doc = st.selectbox("Select Architecture Document", list(doc_map.keys()))
            curr_doc_id = doc_map[selected_doc]

            if st.button("🚀 Generate Traceability Matrix", type="primary"):
                chunks = [c.__dict__ for c in db.query(Chunk).filter(Chunk.document_id == curr_doc_id).all()]
                comps = [c.__dict__ for c in db.query(Component).filter(Component.document_id == curr_doc_id).all()]
                ifs = [i.__dict__ for i in db.query(Interface).filter(Interface.document_id == curr_doc_id).all()]
                ports = [p.__dict__ for p in db.query(Port).filter(Port.document_id == curr_doc_id).all()]

                engine = TraceabilityEngine()
                reqs = engine.extract_requirements(chunks)
                matrix = engine.build_traceability_matrix(reqs, comps, ifs, ports)

                c1, c2, c3 = st.columns(3)
                c1.metric("Total Requirements Identified", matrix.get("total_requirements", 0))
                c2.metric("Requirement Coverage", f"{matrix.get('requirement_coverage_pct', 100)}%")
                c3.metric("Component Coverage", f"{matrix.get('swc_coverage_pct', 100)}%")

                st.markdown("### 📋 Traceability Mapping Grid")
                rows = matrix.get("matrix", [])
                if rows:
                    t_df = pd.DataFrame([{
                        "Req ID": r["requirement_id"],
                        "Description": r["requirement_desc"],
                        "Page": r["source_page"],
                        "Status": r["status"],
                        "Mapped SWCs": ", ".join(r["components"]) if r["components"] else "Unassigned",
                        "Mapped Interfaces": ", ".join(r["interfaces"]) if r["interfaces"] else "None",
                    } for r in rows])
                    st.dataframe(t_df, use_container_width=True)
                else:
                    st.info("No explicit requirement statements extracted.")


# ---------------- TAB 7: INTERACTIVE ARCHITECTURE ----------------
elif nav_choice == "🕸️ Interactive Architecture":
    st.header("🕸️ AUTOSAR SWC Communication & Connection Diagram")
    st.write("Visualize component connectivity, sender-receiver channels, and client-server interactions.")

    with get_db_session() as db:
        docs = db.query(Document).all()
        if not docs:
            st.warning("No documents available.")
        else:
            doc_map = {f"{d.original_filename} (v{d.version or '1.0'})": d.document_id for d in docs}
            selected_doc = st.selectbox("Select Architecture Model", list(doc_map.keys()))
            curr_doc_id = doc_map[selected_doc]

            comps = [c.__dict__ for c in db.query(Component).filter(Component.document_id == curr_doc_id).all()]
            ports = [p.__dict__ for p in db.query(Port).filter(Port.document_id == curr_doc_id).all()]
            deps = [d.__dict__ for d in db.query(Dependency).filter(Dependency.document_id == curr_doc_id).all()]

            mermaid_code = ExportService.generate_mermaid_diagram(comps, ports, deps)

            st.markdown("### 🌐 Component Connectivity Graph (Mermaid)")
            st.markdown(mermaid_code)

            with st.expander("📝 View Mermaid Source Code"):
                st.code(mermaid_code, language="mermaid")


# ---------------- TAB 8: REPORTS & EXPORT ----------------
elif nav_choice == "📑 Report & Export Center":
    st.header("📑 Engineering Report Generator & Model Export")
    st.write("Export formal engineering documentation, AUTOSAR ARXML skeletons, and structured datasets.")

    with get_db_session() as db:
        docs = db.query(Document).all()
        if not docs:
            st.warning("No documents available.")
        else:
            doc_map = {f"{d.original_filename} (v{d.version or '1.0'})": d for d in docs}
            selected_doc = st.selectbox("Select Target Specification", list(doc_map.keys()))
            curr_doc = doc_map[selected_doc]
            curr_doc_id = curr_doc.document_id

            comps = [c.__dict__ for c in db.query(Component).filter(Component.document_id == curr_doc_id).all()]
            ifs = [i.__dict__ for i in db.query(Interface).filter(Interface.document_id == curr_doc_id).all()]
            ports = [p.__dict__ for p in db.query(Port).filter(Port.document_id == curr_doc_id).all()]
            sigs = [s.__dict__ for s in db.query(Signal).filter(Signal.document_id == curr_doc_id).all()]
            deps = [d.__dict__ for d in db.query(Dependency).filter(Dependency.document_id == curr_doc_id).all()]

            exp1, exp2 = st.columns(2)

            with exp1:
                st.subheader("📄 Formal Architecture Report (Markdown)")
                md_report = ReportGenerator.generate_architecture_summary_report(
                    doc_metadata={"filename": curr_doc.original_filename, "version": curr_doc.version or "1.0"},
                    components=comps,
                    interfaces=ifs,
                    ports=ports,
                    signals=sigs,
                    dependencies=deps
                )
                st.download_button(
                    label="📥 Download Architecture Report (.md)",
                    data=md_report,
                    file_name=f"{curr_doc_id}_Architecture_Report.md",
                    mime="text/markdown"
                )

                st.subheader("⚡ AUTOSAR ARXML Skeleton")
                arxml_content = ExportService.generate_arxml(comps, ifs, ports, project_name=curr_doc_id)
                st.download_button(
                    label="📥 Download AUTOSAR 4.x ARXML (.arxml)",
                    data=arxml_content,
                    file_name=f"{curr_doc_id}_autosar.arxml",
                    mime="application/xml"
                )

            with exp2:
                st.subheader("📊 Structured JSON & CSV Exports")
                json_data = ExportService.export_json({
                    "document_id": curr_doc_id,
                    "filename": curr_doc.original_filename,
                    "components": comps,
                    "interfaces": ifs,
                    "ports": ports,
                    "signals": sigs
                })
                st.download_button(
                    label="📥 Download Architecture Model (.json)",
                    data=json_data,
                    file_name=f"{curr_doc_id}_model.json",
                    mime="application/json"
                )

                if comps:
                    csv_data = ExportService.export_csv(comps, fieldnames=["name", "component_type", "source_page", "description"])
                    st.download_button(
                        label="📥 Download Components Inventory (.csv)",
                        data=csv_data,
                        file_name=f"{curr_doc_id}_components.csv",
                        mime="text/csv"
                    )

            with st.expander("👀 Preview Generated Architecture Report"):
                st.markdown(md_report)
