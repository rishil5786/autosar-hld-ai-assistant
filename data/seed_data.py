"""
AUTOSAR HLD AI - Database & Vector Store Pre-loader
Ingests the generated sample HLD documents into SQLite and FAISS.
"""

import os
import sys
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.utils.config import settings
from app.backend.database import init_db, get_db_session
from app.backend.models import Document, Project, Chunk, Component, Interface, Port, Signal, Dependency
from app.ingestion.pdf_parser import parse_pdf
from app.ingestion.chunker import chunk_document
from app.embeddings.embedding_service import get_embedding_service
from app.vectorstore.faiss_store import get_faiss_store
from app.extraction.component_extractor import extract_components
from app.extraction.interface_extractor import extract_interfaces
from app.extraction.port_extractor import extract_ports


def seed_database():
    init_db()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.VECTOR_STORE_DIR, exist_ok=True)

    sample_dir = os.path.join(BASE_DIR, "data", "sample_documents")
    sample_files = [
        ("BMS_HLD_Specification_v1.0.pdf", "1.0", "doc_bms_v1"),
        ("BMS_HLD_Specification_v2.0.pdf", "2.0", "doc_bms_v2")
    ]

    with get_db_session() as db:
        # Create Project
        project = db.query(Project).first()
        if not project:
            project = Project(id=1, name="EV Powertrain Platform", description="High-Voltage BMS ECU Architecture", owner_id=1)
            db.add(project)
            db.commit()

        embedding_svc = get_embedding_service()
        vstore = get_faiss_store()

        for fname, version, doc_id in sample_files:
            src_path = os.path.join(sample_dir, fname)
            if not os.path.exists(src_path):
                print(f"File not found: {src_path}")
                continue

            dest_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}_{fname}")
            shutil.copyfile(src_path, dest_path)

            # Check if document already exists
            existing_doc = db.query(Document).filter(Document.document_id == doc_id).first()
            if existing_doc:
                db.query(Chunk).filter(Chunk.document_id == doc_id).delete()
                db.query(Component).filter(Component.document_id == doc_id).delete()
                db.query(Interface).filter(Interface.document_id == doc_id).delete()
                db.query(Port).filter(Port.document_id == doc_id).delete()
                db.query(Dependency).filter(Dependency.document_id == doc_id).delete()
                db.delete(existing_doc)
                db.commit()

            file_size = os.path.getsize(dest_path)
            doc_record = Document(
                document_id=doc_id,
                project_id=project.id,
                filename=f"{doc_id}_{fname}",
                original_filename=fname,
                file_hash=doc_id,
                file_size=file_size,
                version=version,
                status="processing"
            )
            db.add(doc_record)
            db.commit()

            # Parse
            parsed = parse_pdf(dest_path, filename=fname)
            doc_record.page_count = parsed.page_count

            # Chunk
            chunks = chunk_document(parsed, document_id=doc_id)
            chunk_texts = []
            chunk_metas = []
            for ch in chunks:
                db.add(Chunk(
                    chunk_id=ch.chunk_id,
                    document_id=doc_id,
                    document_name=fname,
                    page_number=ch.page_number,
                    section=ch.section,
                    text=ch.text,
                    chunk_index=ch.chunk_index,
                    token_count=ch.token_count,
                    metadata_json=ch.metadata
                ))
                chunk_texts.append(ch.text)
                chunk_metas.append(ch.metadata)

            # Add to vector store
            if chunk_texts:
                embeddings = embedding_svc.embed_texts(chunk_texts)
                if embeddings is not None:
                    vstore.add_vectors(embeddings, chunk_texts, chunk_metas)
                    vstore.save()

            # Extract entities
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

            # Add architectural dependencies
            if version == "1.0":
                db.add(Dependency(document_id=doc_id, source_component="CellVoltageMonitor", target_component="SOC_SOE_Estimator", description="If_CellVoltage"))
                db.add(Dependency(document_id=doc_id, source_component="CellTemperatureMonitor", target_component="SOC_SOE_Estimator", description="If_CellTemperature"))
                db.add(Dependency(document_id=doc_id, source_component="SOC_SOE_Estimator", target_component="ContactorControlManager", description="If_BatteryStateOfCharge"))
                db.add(Dependency(document_id=doc_id, source_component="CellTemperatureMonitor", target_component="ThermalManagementService", description="If_CellTemperature"))
            else:
                db.add(Dependency(document_id=doc_id, source_component="CellVoltageMonitor", target_component="SOC_SOE_Estimator", description="If_CellVoltage"))
                db.add(Dependency(document_id=doc_id, source_component="CellTemperatureMonitor", target_component="SOC_SOE_Estimator", description="If_CellTemperature"))
                db.add(Dependency(document_id=doc_id, source_component="CellVoltageMonitor", target_component="ActiveCellBalancingManager", description="If_CellVoltage"))
                db.add(Dependency(document_id=doc_id, source_component="IsolationMonitor", target_component="ContactorControlManager", description="If_IsolationStatus"))
                db.add(Dependency(document_id=doc_id, source_component="SOC_SOE_Estimator", target_component="ContactorControlManager", description="If_BatteryStateOfCharge"))

            doc_record.status = "processed"
            db.commit()
            print(f"Seeded document: {fname} (ID: {doc_id})")

    print("[SUCCESS] Seeding complete!")


if __name__ == "__main__":
    seed_database()
