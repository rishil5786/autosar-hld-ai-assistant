"""
AUTOSAR HLD AI - Database Models
SQLAlchemy ORM models for all application data.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship, DeclarativeBase
import enum


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ENGINEER = "engineer"
    REVIEWER = "reviewer"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"


class User(Base):
    """User accounts with role-based access."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(200), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.ENGINEER.value)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, nullable=True)

    projects = relationship("Project", back_populates="owner")
    reviews = relationship("Review", back_populates="reviewer")


class Project(Base):
    """Projects grouping related documents."""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="projects")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")


class Document(Base):
    """Uploaded HLD documents."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(64), unique=True, nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False)
    file_size = Column(Integer, nullable=False)
    page_count = Column(Integer, default=0)
    version = Column(String(50), nullable=True)
    status = Column(String(50), default="uploaded")  # uploaded, processing, processed, error
    ocr_used = Column(Boolean, default=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    components = relationship("Component", back_populates="document", cascade="all, delete-orphan")
    interfaces = relationship("Interface", back_populates="document", cascade="all, delete-orphan")
    ports = relationship("Port", back_populates="document", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="document", cascade="all, delete-orphan")
    dependencies = relationship("Dependency", back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    """Track document revisions for comparison."""
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(64), ForeignKey("documents.document_id"), nullable=False)
    version_label = Column(String(100), nullable=False)
    changes_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Chunk(Base):
    """Document chunks for RAG retrieval."""
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_id = Column(String(64), unique=True, nullable=False, index=True)
    document_id = Column(String(64), ForeignKey("documents.document_id"), nullable=False)
    document_name = Column(String(255), nullable=False)
    page_number = Column(Integer, nullable=False)
    section = Column(String(500), nullable=True)
    text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    token_count = Column(Integer, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="chunks")


class Component(Base):
    """Extracted AUTOSAR software components."""
    __tablename__ = "components"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(64), ForeignKey("documents.document_id"), nullable=False)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    component_type = Column(String(100), nullable=True)
    source_page = Column(Integer, nullable=True)
    source_section = Column(String(500), nullable=True)
    confidence = Column(Float, default=1.0)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="components")


class Interface(Base):
    """Extracted AUTOSAR interfaces."""
    __tablename__ = "interfaces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(64), ForeignKey("documents.document_id"), nullable=False)
    name = Column(String(200), nullable=False, index=True)
    interface_type = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    source_page = Column(Integer, nullable=True)
    source_section = Column(String(500), nullable=True)
    related_component = Column(String(200), nullable=True)
    confidence = Column(Float, default=1.0)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="interfaces")


class Port(Base):
    """Extracted AUTOSAR ports."""
    __tablename__ = "ports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(64), ForeignKey("documents.document_id"), nullable=False)
    name = Column(String(200), nullable=False, index=True)
    port_type = Column(String(50), nullable=True)  # provided, required
    direction = Column(String(50), nullable=True)
    interface_name = Column(String(200), nullable=True)
    component_name = Column(String(200), nullable=True)
    source_page = Column(Integer, nullable=True)
    confidence = Column(Float, default=1.0)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="ports")


class Signal(Base):
    """Extracted AUTOSAR signals."""
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(64), ForeignKey("documents.document_id"), nullable=False)
    name = Column(String(200), nullable=False, index=True)
    signal_type = Column(String(100), nullable=True)
    source_component = Column(String(200), nullable=True)
    target_component = Column(String(200), nullable=True)
    interface_name = Column(String(200), nullable=True)
    source_page = Column(Integer, nullable=True)
    confidence = Column(Float, default=1.0)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="signals")


class Dependency(Base):
    """Extracted component dependencies."""
    __tablename__ = "dependencies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(64), ForeignKey("documents.document_id"), nullable=False)
    source_component = Column(String(200), nullable=False)
    target_component = Column(String(200), nullable=False)
    dependency_type = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    source_page = Column(Integer, nullable=True)
    confidence = Column(Float, default=1.0)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="dependencies")


class AnalysisResult(Base):
    """Analysis results including inconsistencies and completeness."""
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(64), nullable=False, index=True)
    analysis_type = Column(String(100), nullable=False)  # inconsistency, completeness, comparison
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(50), nullable=True)  # info, warning, potential_issue, critical
    evidence_json = Column(JSON, nullable=True)
    status = Column(String(50), default=ReviewStatus.PENDING.value)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ChatHistory(Base):
    """Chat conversation history."""
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    document_id = Column(String(64), nullable=True)
    role = Column(String(20), nullable=False)  # user, assistant
    message = Column(Text, nullable=False)
    sources_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Review(Base):
    """Human review of AI-generated findings."""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("analysis_results.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(50), nullable=False)  # accepted, rejected, edited
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    reviewer = relationship("User", back_populates="reviews")


class AuditLog(Base):
    """Audit trail for important actions."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
