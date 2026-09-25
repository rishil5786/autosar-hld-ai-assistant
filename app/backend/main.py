"""
AUTOSAR HLD AI - FastAPI Application
Main application entry point providing REST API for document ingestion,
entity extraction, RAG Q&A, revision comparison, compliance audit, and exports.
"""

import os
import shutil
import uuid
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Query as FastQuery, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.utils.config import settings
from app.utils.logger import logger
from app.backend.database import init_db, get_db, get_db_session
from app.backend.models import Document, Project, Chunk, Component, Interface, Port, Signal, Dependency, AnalysisResult
from app.backend.schemas import (
    QueryRequest, QueryResponse, Citation, ChunkResponse,
    DocumentResponse, DocumentStats, ComponentResponse, InterfaceResponse,
    PortResponse, SignalResponse, DependencyResponse
)

# Core services
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Starting AUTOSAR HLD AI Backend Service...")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.VECTOR_STORE_DIR, exist_ok=True)
    init_db()
    yield
    logger.info("Shutting down AUTOSAR HLD AI Backend Service...")


app = FastAPI(
    title="AUTOSAR HLD AI Document Analysis API",
    description="Automated Extraction, RAG Q&A, Revision Comparison, and Consistency Validation for AUTOSAR HLDs",
    version="1.0.0",
    lifespan=lifespan
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": "AUTOSAR HLD AI Document Analysis API",
        "status": "online",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "database": "connected", "rag_pipeline": "ready"}


# --- Document Ingestion Endpoints ---

@app.post("/api/documents/upload", response_model=Dict[str, Any])
async def upload_document(
    file: UploadFile = File(...),
    version: Optional[str] = Form("1.0"),
    project_id: Optional[int] = Form(1),
    db: Session = Depends(get_db)
):
    """
    Upload an AUTOSAR HLD PDF document and save it for processing.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    file_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}_{file.filename}")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)

    # Ensure default project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        project = Project(id=1, name="Default AUTOSAR Project", description="Main System ECU Design", owner_id=1)
        db.add(project)
        db.commit()

    db_doc = Document(
        document_id=doc_id,
        project_id=project.id,
        filename=os.path.basename(file_path),
        original_filename=file.filename,
        file_hash=doc_id,
        file_size=file_size,
        version=version,
        status="uploaded"
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    logger.info(f"Document uploaded: {file.filename} (ID: {doc_id})")
    return {
        "message": "Document uploaded successfully",
        "document_id": doc_id,
        "filename": file.filename,
        "size_bytes": file_size,
        "status": "uploaded"
    }


@app.post("/api/ingestion/process/{doc_id}")
def process_document(doc_id: str, db: Session = Depends(get_db)):
    """
    Ingest, parse, chunk, embed, and extract AUTOSAR architecture entities from the document.
    """
    db_doc = db.query(Document).filter(Document.document_id == doc_id).first()
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = os.path.join(settings.UPLOAD_DIR, db_doc.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Underlying document file not found on disk")

    db_doc.status = "processing"
    db.commit()

    try:
        # 1. Parse PDF
        parsed_doc = parse_pdf(file_path, filename=db_doc.original_filename)
        db_doc.page_count = parsed_doc.page_count

        # 2. Chunk Document
        chunks = chunk_document(parsed_doc, document_id=doc_id)

        # Clear existing chunks for this document
        db.query(Chunk).filter(Chunk.document_id == doc_id).delete()

        # Save chunks to SQLite and collect texts/metas for vector embedding
        chunk_texts = []
        chunk_metas = []
        for ch in chunks:
            db_chunk = Chunk(
                chunk_id=ch.chunk_id,
                document_id=doc_id,
                document_name=db_doc.original_filename,
                page_number=ch.page_number,
                section=ch.section,
                text=ch.text,
                chunk_index=ch.chunk_index,
                token_count=ch.token_count,
                metadata_json=ch.metadata
            )
            db.add(db_chunk)
            chunk_texts.append(ch.text)
            chunk_metas.append(ch.metadata)

        # 3. Add to FAISS Vector Store
        embedding_svc = get_embedding_service()
        vstore = get_faiss_store()
        if chunk_texts:
            embeddings = embedding_svc.embed_texts(chunk_texts)
            if embeddings is not None:
                vstore.add_vectors(embeddings, chunk_texts, chunk_metas)
                vstore.save()

        # 4. Extract Architecture Entities (Components, Ports, Interfaces)
        # Clear existing extracted entities
        db.query(Component).filter(Component.document_id == doc_id).delete()
        db.query(Interface).filter(Interface.document_id == doc_id).delete()
        db.query(Port).filter(Port.document_id == doc_id).delete()
        db.query(Dependency).filter(Dependency.document_id == doc_id).delete()

        all_extracted_comps = []
        all_extracted_ifs = []
        all_extracted_ports = []

        for page in parsed_doc.pages:
            p_num = page.page_number
            p_text = page.text
            
            # Extract components
            page_comps = extract_components(p_text, page_number=p_num)
            for c in page_comps:
                comp_obj = Component(
                    document_id=doc_id,
                    name=c["name"],
                    description=c.get("description", ""),
                    component_type=c.get("component_type", "Component"),
                    source_page=p_num,
                    confidence=c.get("confidence", 0.8)
                )
                db.add(comp_obj)
                all_extracted_comps.append(c)

            # Extract interfaces
            page_ifs = extract_interfaces(p_text, page_number=p_num)
            for i in page_ifs:
                if_obj = Interface(
                    document_id=doc_id,
                    name=i["name"],
                    interface_type=i.get("interface_type", "SenderReceiver"),
                    description=i.get("description", ""),
                    related_component=i.get("related_component", ""),
                    source_page=p_num,
                    confidence=i.get("confidence", 0.8)
                )
                db.add(if_obj)
                all_extracted_ifs.append(i)

            # Extract ports
            page_ports = extract_ports(p_text, page_number=p_num)
            for p in page_ports:
                port_obj = Port(
                    document_id=doc_id,
                    name=p["name"],
                    port_type=p.get("port_type", "Provided"),
                    direction=p.get("direction", "Out"),
                    interface_name=p.get("interface_name", ""),
                    component_name=p.get("component_name", ""),
                    source_page=p_num,
                    confidence=p.get("confidence", 0.8)
                )
                db.add(port_obj)
                all_extracted_ports.append(p)

        db_doc.status = "processed"
        db.commit()

        logger.info(f"Successfully processed document {doc_id}: {len(chunks)} chunks, {len(all_extracted_comps)} SWCs, {len(all_extracted_ifs)} Interfaces, {len(all_extracted_ports)} Ports.")
        return {
            "message": "Document processed and indexed successfully",
            "document_id": doc_id,
            "page_count": db_doc.page_count,
            "chunks_count": len(chunks),
            "components_count": len(all_extracted_comps),
            "interfaces_count": len(all_extracted_ifs),
            "ports_count": len(all_extracted_ports),
            "status": "processed"
        }

    except Exception as e:
        logger.error(f"Error processing document {doc_id}: {e}", exc_info=True)
        db_doc.status = "error"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents", response_model=List[DocumentResponse])
def get_documents(db: Session = Depends(get_db)):
    """List all documents."""
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return docs


@app.get("/api/documents/{doc_id}")
def get_document(doc_id: str, db: Session = Depends(get_db)):
    """Get single document details."""
    doc = db.query(Document).filter(Document.document_id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    comp_count = db.query(Component).filter(Component.document_id == doc_id).count()
    if_count = db.query(Interface).filter(Interface.document_id == doc_id).count()
    port_count = db.query(Port).filter(Port.document_id == doc_id).count()
    chunk_count = db.query(Chunk).filter(Chunk.document_id == doc_id).count()

    return {
        "id": doc.id,
        "document_id": doc.document_id,
        "filename": doc.filename,
        "original_filename": doc.original_filename,
        "file_size": doc.file_size,
        "page_count": doc.page_count,
        "version": doc.version,
        "status": doc.status,
        "created_at": doc.created_at,
        "components_count": comp_count,
        "interfaces_count": if_count,
        "ports_count": port_count,
        "chunks_count": chunk_count
    }


# --- RAG Q&A Endpoints ---

@app.post("/api/rag/query", response_model=QueryResponse)
def query_rag(req: QueryRequest, db: Session = Depends(get_db)):
    """
    Perform Retrieval-Augmented Generation (RAG) query on ingested AUTOSAR documents.
    """
    result = run_rag_query(question=req.question, document_id=req.document_id, top_k=req.top_k)
    return result


# --- Extraction & Entities Endpoints ---

@app.get("/api/extraction/{doc_id}")
def get_extracted_entities(doc_id: str, db: Session = Depends(get_db)):
    """Get all extracted architectural entities for a document."""
    comps = db.query(Component).filter(Component.document_id == doc_id).all()
    ifs = db.query(Interface).filter(Interface.document_id == doc_id).all()
    ports = db.query(Port).filter(Port.document_id == doc_id).all()
    signals = db.query(Signal).filter(Signal.document_id == doc_id).all()
    deps = db.query(Dependency).filter(Dependency.document_id == doc_id).all()

    return {
        "document_id": doc_id,
        "components": [{"name": c.name, "component_type": c.component_type, "description": c.description, "source_page": c.source_page, "confidence": c.confidence} for c in comps],
        "interfaces": [{"name": i.name, "interface_type": i.interface_type, "related_component": i.related_component, "description": i.description, "source_page": i.source_page, "confidence": i.confidence} for i in ifs],
        "ports": [{"name": p.name, "port_type": p.port_type, "direction": p.direction, "interface_name": p.interface_name, "component_name": p.component_name, "source_page": p.source_page} for p in ports],
        "signals": [{"name": s.name, "signal_type": s.signal_type, "source_component": s.source_component, "target_component": s.target_component, "source_page": s.source_page} for s in signals],
        "dependencies": [{"source_component": d.source_component, "target_component": d.target_component, "dependency_type": d.dependency_type, "description": d.description} for d in deps]
    }


# --- Analysis & Compliance Endpoints ---

@app.get("/api/analysis/inconsistencies/{doc_id}")
def run_inconsistency_audit(doc_id: str, db: Session = Depends(get_db)):
    """Run full AUTOSAR consistency and compliance validation on a document."""
    comps = [c.__dict__ for c in db.query(Component).filter(Component.document_id == doc_id).all()]
    ifs = [i.__dict__ for i in db.query(Interface).filter(Interface.document_id == doc_id).all()]
    ports = [p.__dict__ for p in db.query(Port).filter(Port.document_id == doc_id).all()]
    signals = [s.__dict__ for s in db.query(Signal).filter(Signal.document_id == doc_id).all()]
    deps = [d.__dict__ for d in db.query(Dependency).filter(Dependency.document_id == doc_id).all()]

    checker = InconsistencyChecker()
    audit_results = checker.check_document(
        document_id=doc_id,
        components=comps,
        interfaces=ifs,
        ports=ports,
        signals=signals,
        dependencies=deps
    )
    return audit_results


@app.get("/api/analysis/traceability/{doc_id}")
def get_traceability_matrix(doc_id: str, db: Session = Depends(get_db)):
    """Generate requirement-to-architecture traceability matrix."""
    chunks = [c.__dict__ for c in db.query(Chunk).filter(Chunk.document_id == doc_id).all()]
    comps = [c.__dict__ for c in db.query(Component).filter(Component.document_id == doc_id).all()]
    ifs = [i.__dict__ for i in db.query(Interface).filter(Interface.document_id == doc_id).all()]
    ports = [p.__dict__ for p in db.query(Port).filter(Port.document_id == doc_id).all()]

    engine = TraceabilityEngine()
    reqs = engine.extract_requirements(chunks)
    matrix = engine.build_traceability_matrix(reqs, comps, ifs, ports)
    return matrix


@app.post("/api/analysis/compare")
def compare_revisions(doc_id_1: str = FastQuery(...), doc_id_2: str = FastQuery(...), db: Session = Depends(get_db)):
    """Compare two document revisions and generate structural & semantic diffs."""
    doc1 = db.query(Document).filter(Document.document_id == doc_id_1).first()
    doc2 = db.query(Document).filter(Document.document_id == doc_id_2).first()

    if not doc1 or not doc2:
        raise HTTPException(status_code=404, detail="One or both documents not found")

    def load_doc_data(d):
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

    v1_data = load_doc_data(doc1)
    v2_data = load_doc_data(doc2)

    comparator = RevisionComparator()
    diff_report = comparator.compare_documents(v1_data, v2_data)
    return diff_report


# --- Export Endpoints ---

@app.get("/api/export/arxml/{doc_id}")
def export_arxml(doc_id: str, db: Session = Depends(get_db)):
    """Export document architecture as an AUTOSAR 4.x compliant ARXML file."""
    comps = [c.__dict__ for c in db.query(Component).filter(Component.document_id == doc_id).all()]
    ifs = [i.__dict__ for i in db.query(Interface).filter(Interface.document_id == doc_id).all()]
    ports = [p.__dict__ for p in db.query(Port).filter(Port.document_id == doc_id).all()]

    arxml_content = ExportService.generate_arxml(comps, ifs, ports, project_name=doc_id)
    return Response(
        content=arxml_content,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename={doc_id}_autosar.arxml"}
    )


@app.get("/api/export/mermaid/{doc_id}")
def export_mermaid(doc_id: str, db: Session = Depends(get_db)):
    """Generate Mermaid.js architecture flowchart."""
    comps = [c.__dict__ for c in db.query(Component).filter(Component.document_id == doc_id).all()]
    ports = [p.__dict__ for p in db.query(Port).filter(Port.document_id == doc_id).all()]
    deps = [d.__dict__ for d in db.query(Dependency).filter(Dependency.document_id == doc_id).all()]

    mermaid_code = ExportService.generate_mermaid_diagram(comps, ports, deps)
    return {"mermaid_code": mermaid_code}


@app.get("/api/reports/architecture/{doc_id}")
def get_architecture_report(doc_id: str, db: Session = Depends(get_db)):
    """Generate Markdown architecture report."""
    doc = db.query(Document).filter(Document.document_id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    comps = [c.__dict__ for c in db.query(Component).filter(Component.document_id == doc_id).all()]
    ifs = [i.__dict__ for i in db.query(Interface).filter(Interface.document_id == doc_id).all()]
    ports = [p.__dict__ for p in db.query(Port).filter(Port.document_id == doc_id).all()]
    signals = [s.__dict__ for s in db.query(Signal).filter(Signal.document_id == doc_id).all()]
    deps = [d.__dict__ for d in db.query(Dependency).filter(Dependency.document_id == doc_id).all()]

    checker = InconsistencyChecker()
    audit_results = checker.check_document(doc_id, comps, ifs, ports, signals, deps)

    md_report = ReportGenerator.generate_architecture_summary_report(
        doc_metadata={"filename": doc.original_filename, "version": doc.version or "1.0"},
        components=comps,
        interfaces=ifs,
        ports=ports,
        signals=signals,
        dependencies=deps,
        audit_summary=audit_results
    )

    return PlainTextResponse(content=md_report, media_type="text/markdown")
