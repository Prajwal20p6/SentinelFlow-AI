"""
SentinelFlow AI — Knowledge Base Router
Endpoints for document uploads, metadata indexing, search, updates, and approvals.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List

from ..core.database import get_db
from ..middleware.auth import get_current_user, require_role
from ..models.models import User, KnowledgeDocument
from ..schemas.schemas import KnowledgeDocumentResponse, KnowledgeDocumentUpdateRequest, KnowledgeSearchResponse
from ..services.knowledge_service import KnowledgeBaseService

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])

@router.post("/documents", response_model=KnowledgeDocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    category: str = Form(...),
    subcategory: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("engineer")),
):
    """Upload and auto-extract text from DOCX, PDF, MD, or TXT playbooks."""
    file_content = await file.read()
    content = KnowledgeBaseService.extract_text(file.filename, file_content)

    doc = KnowledgeBaseService.create_document(
        db=db,
        title=title,
        filename=file.filename,
        category=category,
        subcategory=subcategory,
        tags=tags,
        author=current_user.full_name or current_user.email,
        content=content
    )
    return doc

@router.get("/documents", response_model=List[KnowledgeDocumentResponse])
def list_documents(
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status (draft, approved, archived)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List knowledge base recovery documents."""
    query = db.query(KnowledgeDocument)
    if category:
        query = query.filter(KnowledgeDocument.category == category)
    if status:
        query = query.filter(KnowledgeDocument.status == status)
    else:
        # Exclude archived by default
        query = query.filter(KnowledgeDocument.status != "archived")
        
    return query.order_by(KnowledgeDocument.updated_at.desc()).all()

@router.patch("/documents/{doc_id}", response_model=KnowledgeDocumentResponse)
def update_document(
    doc_id: int,
    body: KnowledgeDocumentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("engineer")),
):
    """Modify document details and re-index vector representations."""
    doc = KnowledgeBaseService.update_document(
        db=db,
        doc_id=doc_id,
        title=body.title,
        category=body.category,
        subcategory=body.subcategory,
        tags=body.tags,
        content=body.content,
        version=body.version
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.delete("/documents/{doc_id}", response_model=KnowledgeDocumentResponse)
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Soft-delete/archive document (Admin only)."""
    doc = KnowledgeBaseService.archive_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.post("/documents/{doc_id}/approve", response_model=KnowledgeDocumentResponse)
def approve_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Mark draft playbooks as approved for Autopilot recommendation pools (Admin only)."""
    doc = KnowledgeBaseService.approve_document(
        db=db,
        doc_id=doc_id,
        approver=current_user.full_name or current_user.email
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.get("/search", response_model=List[KnowledgeSearchResponse])
def search_knowledge_base(
    q: str = Query(..., description="Semantic search query"),
    category: Optional[str] = Query(None, description="Filter search by category"),
    limit: int = Query(5, description="Search results limit"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Perform semantic vector similarity search across all indexed playbook chunks."""
    from ..core.vector_db import search_similar_runbooks
    hits = search_similar_runbooks(
        query=q,
        limit=limit,
        category_filter=category
    )
    return hits


@router.post("/ask")
def ask_knowledge_assistant(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    AI Knowledge Assistant Endpoint.
    Intelligently routes queries to Conversational, Factual Platform Knowledge, or Vector RAG Retrieval.
    """
    from ..core.vector_db import search_similar_runbooks
    from ..services.execution_mode_service import ExecutionModeService

    q_raw = body.get("question", "").strip()
    if not q_raw:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    q = q_raw.lower()

    # 1. Conversational Greetings (No expensive vector search)
    if q in ["hi", "hello", "hey", "greetings", "good morning", "good evening", "who are you"]:
        return {
            "question": q_raw,
            "answer": "Hello! I am the SentinelFlow AI Knowledge & SecOps Assistant. I can answer questions about system infrastructure, platform governance, active operating modes, threat mitigation, and automated runbook SOPs.",
            "intent": "CONVERSATIONAL",
            "rag_sources": []
        }

    # 2. Factual System / Company / Operating Mode Knowledge
    if "sentinelflow" in q or "company" in q or "platform" in q:
        return {
            "question": q_raw,
            "answer": "SentinelFlow AI is an autonomous, AI-driven incident response and infrastructure resilience platform for Kubernetes microservices. It combines real-time telemetry monitoring, Mastra workflow orchestration, Enkrypt AI safety guardrails, Qdrant vector RAG retrieval, and cryptographic audit ledgers.",
            "intent": "PLATFORM_KNOWLEDGE",
            "llm_provider_mode": "DETERMINISTIC_PROJECT_KNOWLEDGE",
            "rag_sources": []
        }
    elif "agent" in q or "handle incident" in q or "workflow" in q or "approval" in q:
        return {
            "question": q_raw,
            "answer": "SentinelFlow AI coordinates 4 specialized agents in a Mastra workflow: 1) Root Cause Analysis (RCA) Agent, 2) Threat Intelligence Agent, 3) Prioritization Agent, and 4) Remediation Agent. Below the configured confidence threshold, remediation pauses at an approval gate for engineer sign-off.",
            "intent": "AGENT_WORKFLOW",
            "llm_provider_mode": "DETERMINISTIC_WORKFLOW_KNOWLEDGE",
            "rag_sources": []
        }
    elif "fallback" in q or "qdrant" in q or "enkrypt" in q:
        return {
            "question": q_raw,
            "answer": "SentinelFlow AI features transparent 4-tier vector fallback (Qdrant Cloud -> ChromaDB -> FAISS -> In-Memory) and Enkrypt AI safety envelope fallback (Cloud API -> Local Regex Guardrails). Every fallback response carries an explicit `is_simulated: true` badge in the UI.",
            "intent": "ARCHITECTURE_FALLBACK",
            "llm_provider_mode": "DETERMINISTIC_ARCHITECTURE_KNOWLEDGE",
            "rag_sources": []
        }
    elif "operating mode" in q or "autonomy mode" in q or "governance mode" in q:
        cfg = ExecutionModeService.get_config(db)
        return {
            "question": q_raw,
            "answer": f"The current system operating mode is **{cfg.mode}** (Min Confidence: {cfg.min_confidence_score}%, Rate Limit: {cfg.rate_limit_per_minute}/min, Max Blast Radius: {cfg.max_blast_radius} services). Under {cfg.mode} mode, remediation actions require operator sign-off before auto-execution.",
            "intent": "SYSTEM_STATE",
            "llm_provider_mode": "DETERMINISTIC_STATE_KNOWLEDGE",
            "rag_sources": []
        }
    elif "what is cpu" in q or "cpu exhaustion" in q or "what is memory" in q:
        hits = search_similar_runbooks("CPU Exhaustion", limit=2)
        return {
            "question": q_raw,
            "answer": "CPU/Memory exhaustion occurs when microservice workload demand exceeds node resource capacity (>90% utilization). SentinelFlow AI mitigates this by scaling horizontal pod replicas or performing dynamic pod restarts.",
            "intent": "TECHNICAL_EXPLANATION",
            "llm_provider_mode": "DETERMINISTIC_RAG_FALLBACK",
            "rag_sources": hits
        }

    # 3. Vector RAG Retrieval over Runbooks & SOPs
    hits = search_similar_runbooks(q_raw, limit=3)
    if hits:
        top_title = hits[0].get("title", "Runbook SOP")
        top_content = hits[0].get("content", "")
        answer = f"Based on retrieved RAG knowledge from **{top_title}**:\n\n{top_content}"
    else:
        answer = f"SentinelFlow AI Knowledge Assistant processed '{q_raw}'. No exact matching runbook SOP was found in vector memory, but general Kubernetes isolation policies apply."

    return {
        "question": q_raw,
        "answer": answer,
        "intent": "RAG_RETRIEVAL",
        "llm_provider_mode": "DETERMINISTIC_VECTOR_SEARCH",
        "rag_sources": hits
    }
