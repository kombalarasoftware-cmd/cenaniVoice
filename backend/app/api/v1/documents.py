"""
Agent Documents API Endpoints

Handles file uploads and document management for agent RAG.
"""

import os
import logging
from typing import List
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.models.models import Agent, AgentDocument, DocumentChunk
from app.models import User
from app.api.v1.auth import get_current_user
from app.schemas.schemas import AgentDocumentResponse, DocumentSearchRequest, DocumentSearchResponse, DocumentChunkResponse
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents/{agent_id}/documents", tags=["Agent Documents"])

# Allowed file types
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def get_file_extension(filename: str) -> str:
    """Extract and validate file extension"""
    if '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[1].lower()


async def process_document_background(
    document_id: int,
    agent_id: int,
    file_content: bytes,
    file_type: str,
):
    """Background task to process document using async session"""
    try:
        async with AsyncSessionLocal() as db:
            # Update status to processing
            doc = await db.get(AgentDocument, document_id)
            if not doc:
                return

            doc.status = "processing"
            await db.commit()

            # Process document
            service = DocumentService(db)
            chunk_count, token_count = await service.process_document(
                document_id, agent_id, file_content, file_type
            )

            # Update document with results
            doc.status = "ready"
            doc.chunk_count = chunk_count
            doc.token_count = token_count
            await db.commit()

            logger.info(f"Document {document_id} processed: {chunk_count} chunks, {token_count} tokens")

    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        try:
            async with AsyncSessionLocal() as db:
                doc = await db.get(AgentDocument, document_id)
                if doc:
                    doc.status = "error"
                    doc.error_message = str(e)[:500]
                    await db.commit()
        except Exception as inner_e:
            logger.error(f"Failed to update document error status: {inner_e}")


@router.post("/upload", response_model=AgentDocumentResponse)
async def upload_document(
    agent_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document to an agent for RAG processing.

    Supported formats: PDF, TXT, DOCX
    Max file size: 10 MB

    The document will be processed in the background:
    1. Parse document text
    2. Split into chunks
    3. Generate embeddings
    4. Store for semantic search
    """
    # Validate agent exists
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Validate file extension
    ext = get_file_extension(file.filename or "")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Validate file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)} MB"
        )

    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    # Create document record
    document = AgentDocument(
        agent_id=agent_id,
        filename=file.filename or "document",
        file_type=ext,
        file_size=file_size,
        status="pending"
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Start background processing (uses async session internally)
    background_tasks.add_task(
        process_document_background,
        document.id,
        agent_id,
        file_content,
        ext,
    )

    return document


@router.get("/", response_model=List[AgentDocumentResponse])
async def list_documents(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents for an agent"""
    # Validate agent exists
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    documents = (
        db.query(AgentDocument)
        .filter(AgentDocument.agent_id == agent_id)
        .order_by(AgentDocument.created_at.desc())
        .all()
    )
    return documents


@router.get("/{document_id}", response_model=AgentDocumentResponse)
async def get_document(
    agent_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific document"""
    document = db.get(AgentDocument, document_id)
    if not document or document.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete("/{document_id}")
async def delete_document(
    agent_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document and its chunks"""
    document = db.get(AgentDocument, document_id)
    if not document or document.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete document (chunks are cascade deleted)
    db.delete(document)
    db.commit()

    return {"success": True, "message": "Document deleted"}


@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(
    agent_id: int,
    request: DocumentSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Semantic search across agent's documents.

    Uses OpenAI embeddings and pgvector for similarity search.
    """
    # Validate agent exists
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Use async session for vector search operations
    async with AsyncSessionLocal() as async_db:
        service = DocumentService(async_db)
        results = await service.semantic_search(
            agent_id=agent_id,
            query=request.query,
            limit=request.limit
        )

    return DocumentSearchResponse(
        query=request.query,
        results=[
            DocumentChunkResponse(
                id=r["id"],
                content=r["content"],
                chunk_index=r["chunk_index"],
                score=r["score"],
                document_filename=r["document_filename"]
            )
            for r in results
        ],
        total_found=len(results)
    )
