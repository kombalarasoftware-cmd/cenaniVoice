"""
Knowledge Base API Endpoints
============================
RAG (Retrieval Augmented Generation) için Knowledge Base yönetimi
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.core.database import get_db
from app.models.models import KnowledgeBase, KnowledgeDocument

router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])


# ============================================================================
# Schemas
# ============================================================================

class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 1000
    chunk_overlap: int = 200


class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class KnowledgeBaseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    total_documents: int
    total_chunks: int
    total_tokens: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeDocumentResponse(BaseModel):
    id: int
    name: str
    file_type: str
    file_size: int
    status: str
    error_message: Optional[str]
    chunk_count: int
    token_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class AvailableVariablesResponse(BaseModel):
    """Available greeting variables"""
    variables: dict


# ============================================================================
# Knowledge Base Endpoints
# ============================================================================

@router.get("", response_model=List[KnowledgeBaseResponse])
async def list_knowledge_bases(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """List all knowledge bases"""
    return db.query(KnowledgeBase)\
        .order_by(KnowledgeBase.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()


@router.post("", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    db: Session = Depends(get_db)
):
    """Create a new knowledge base"""
    kb = KnowledgeBase(
        name=data.name,
        description=data.description,
        embedding_model=data.embedding_model,
        chunk_size=data.chunk_size,
        chunk_overlap=data.chunk_overlap,
        status="ready"  # No documents yet
    )

    db.add(kb)
    db.commit()
    db.refresh(kb)

    return kb


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific knowledge base"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()

    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    return kb


@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: int,
    data: KnowledgeBaseUpdate,
    db: Session = Depends(get_db)
):
    """Update a knowledge base"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()

    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    if data.name is not None:
        kb.name = data.name
    if data.description is not None:
        kb.description = data.description

    db.commit()
    db.refresh(kb)

    return kb


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    kb_id: int,
    db: Session = Depends(get_db)
):
    """Delete a knowledge base and all its documents"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()

    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    db.delete(kb)
    db.commit()


# ============================================================================
# Document Endpoints
# ============================================================================

@router.get("/{kb_id}/documents", response_model=List[KnowledgeDocumentResponse])
async def list_documents(
    kb_id: int,
    db: Session = Depends(get_db)
):
    """List all documents in a knowledge base"""
    return db.query(KnowledgeDocument)\
        .filter(KnowledgeDocument.knowledge_base_id == kb_id)\
        .order_by(KnowledgeDocument.created_at.desc())\
        .all()


@router.post("/{kb_id}/documents", response_model=KnowledgeDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a document to a knowledge base"""
    # Verify KB exists
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()

    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # Validate file type
    allowed_types = [".pdf", ".txt", ".docx", ".doc", ".csv", ".xlsx", ".md"]
    file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""

    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed: {', '.join(allowed_types)}"
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Create document record
    doc = KnowledgeDocument(
        name=file.filename,
        file_type=file_ext.lstrip("."),
        file_size=file_size,
        status="pending",  # Will be processed by background task
        knowledge_base_id=kb_id
    )

    db.add(doc)
    db.commit()
    db.refresh(doc)

    # TODO: Trigger background task to process document
    # - Extract text
    # - Split into chunks
    # - Generate embeddings
    # - Store in vector DB

    return doc


@router.delete("/{kb_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    kb_id: int,
    doc_id: int,
    db: Session = Depends(get_db)
):
    """Delete a document from a knowledge base"""
    doc = db.query(KnowledgeDocument)\
        .filter(KnowledgeDocument.id == doc_id)\
        .filter(KnowledgeDocument.knowledge_base_id == kb_id)\
        .first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(doc)
    db.commit()


# ============================================================================
# Query Endpoint (RAG)
# ============================================================================

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class QueryResult(BaseModel):
    content: str
    document_name: str
    similarity_score: float
    metadata: Optional[dict] = None


class QueryResponse(BaseModel):
    query: str
    results: List[QueryResult]
    context: str  # Combined context for LLM


@router.post("/{kb_id}/query", response_model=QueryResponse)
async def query_knowledge_base(
    kb_id: int,
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """
    Query a knowledge base using semantic search
    Returns relevant chunks that can be used as context for LLM
    """
    # Verify KB exists
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()

    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # TODO: Implement actual vector search
    # 1. Generate embedding for query using OpenAI
    # 2. Search vector DB for similar chunks
    # 3. Return top_k results

    # Placeholder response
    return QueryResponse(
        query=request.query,
        results=[],
        context="[RAG henüz aktif değil - Vector DB entegrasyonu gerekli]"
    )


# ============================================================================
# Greeting Variables Endpoint
# ============================================================================

@router.get("/greeting/variables", response_model=AvailableVariablesResponse)
async def get_greeting_variables():
    """Get list of available greeting variables"""
    from app.services.greeting_processor import get_available_variables
    
    return AvailableVariablesResponse(
        variables=get_available_variables()
    )


class GreetingPreviewRequest(BaseModel):
    template: str
    sample_data: Optional[dict] = None


class GreetingPreviewResponse(BaseModel):
    preview: str
    variables_used: List[str]
    unknown_variables: List[str]


@router.post("/greeting/preview", response_model=GreetingPreviewResponse)
async def preview_greeting(request: GreetingPreviewRequest):
    """Preview a greeting template with sample data"""
    from app.services.greeting_processor import validate_greeting_template, process_greeting
    
    validation = validate_greeting_template(request.template)
    
    preview = validation["preview"]
    if request.sample_data:
        preview = process_greeting(request.template, request.sample_data, "VoiceAI Agent")
    
    return GreetingPreviewResponse(
        preview=preview,
        variables_used=validation["variables_used"],
        unknown_variables=validation["unknown_variables"]
    )
