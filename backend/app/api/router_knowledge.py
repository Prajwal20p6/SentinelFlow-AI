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
