"""
AUTOSAR HLD AI - Pydantic Schemas
Request/response schemas for the API and data validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# --- Auth ---
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=6)
    full_name: str
    role: Optional[str] = "engineer"


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    full_name: str


class UserInfo(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool


# --- Project ---
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    created_at: datetime
    document_count: int = 0


# --- Document ---
class DocumentResponse(BaseModel):
    id: int
    document_id: str
    project_id: int
    filename: str
    original_filename: str
    file_size: int
    page_count: int
    version: Optional[str]
    status: str
    ocr_used: bool
    created_at: datetime
    processed_at: Optional[datetime]


class DocumentStats(BaseModel):
    total_documents: int = 0
    total_components: int = 0
    total_interfaces: int = 0
    total_ports: int = 0
    total_signals: int = 0
    total_dependencies: int = 0
    total_issues: int = 0


# --- Chunk ---
class ChunkResponse(BaseModel):
    chunk_id: str
    document_name: str
    page_number: int
    section: Optional[str]
    text: str


# --- Query ---
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    document_id: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)


class Citation(BaseModel):
    document_name: str
    page_number: int
    section: Optional[str]
    text_excerpt: str
    relevance_score: float = 0.0


class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation] = []
    llm_available: bool = True
    groundedness: str = "grounded"  # grounded, partial, ungrounded
    retrieved_chunks: List[ChunkResponse] = []


# --- Components ---
class ComponentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    component_type: Optional[str]
    source_page: Optional[int]
    source_section: Optional[str]
    confidence: float
    interfaces: List[str] = []
    ports: List[str] = []
    dependencies: List[str] = []


class InterfaceResponse(BaseModel):
    id: int
    name: str
    interface_type: Optional[str]
    description: Optional[str]
    source_page: Optional[int]
    related_component: Optional[str]
    confidence: float


class PortResponse(BaseModel):
    id: int
    name: str
    port_type: Optional[str]
    direction: Optional[str]
    interface_name: Optional[str]
    component_name: Optional[str]
    source_page: Optional[int]
    confidence: float


class SignalResponse(BaseModel):
    id: int
    name: str
    signal_type: Optional[str]
    source_component: Optional[str]
    target_component: Optional[str]
    interface_name: Optional[str]
    source_page: Optional[int]
    confidence: float


class DependencyResponse(BaseModel):
    id: int
    source_component: str
    target_component: str
    dependency_type: Optional[str]
    description: Optional[str]
    source_page: Optional[int]
    confidence: float


# --- Analysis ---
class AnalysisResultResponse(BaseModel):
    id: int
    analysis_type: str
    title: str
    description: Optional[str]
    severity: Optional[str]
    evidence: Optional[Dict[str, Any]]
    status: str
    created_at: datetime


class ReviewRequest(BaseModel):
    status: str  # accepted, rejected, edited
    comment: Optional[str] = None


# --- Comparison ---
class ComparisonRequest(BaseModel):
    document_id_1: str
    document_id_2: str


class ComparisonResult(BaseModel):
    added_components: List[str] = []
    removed_components: List[str] = []
    modified_components: List[Dict[str, Any]] = []
    added_interfaces: List[str] = []
    removed_interfaces: List[str] = []
    modified_interfaces: List[Dict[str, Any]] = []
    added_ports: List[str] = []
    removed_ports: List[str] = []
    added_signals: List[str] = []
    removed_signals: List[str] = []
    added_dependencies: List[Dict[str, str]] = []
    removed_dependencies: List[Dict[str, str]] = []
    summary: str = ""
    evidence: List[Dict[str, Any]] = []
