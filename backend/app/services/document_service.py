"""
Document Processing Service for RAG (Retrieval Augmented Generation)

This service handles:
- Document parsing (PDF, TXT, DOCX)
- Text chunking with overlap
- OpenAI embedding generation
- PostgreSQL pgvector storage
- Semantic search
"""

import os
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from io import BytesIO

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger(__name__)

# Embedding model configuration
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
CHUNK_SIZE = 500  # tokens (approximately 375 words)
CHUNK_OVERLAP = 100  # tokens


class DocumentService:
    """Service for document processing and semantic search"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.openai_api_key = settings.OPENAI_API_KEY
    
    # ========================================
    # Document Parsing
    # ========================================
    
    async def parse_document(self, file_content: bytes, file_type: str) -> str:
        """
        Parse document content based on file type.
        
        Args:
            file_content: Raw file bytes
            file_type: File extension (pdf, txt, docx)
            
        Returns:
            Extracted text content
        """
        file_type = file_type.lower().strip('.')
        
        if file_type == 'txt':
            return self._parse_txt(file_content)
        elif file_type == 'pdf':
            return await self._parse_pdf(file_content)
        elif file_type == 'docx':
            return await self._parse_docx(file_content)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    def _parse_txt(self, content: bytes) -> str:
        """Parse plain text file"""
        # Try UTF-8 first, then fallback to other encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1254', 'iso-8859-9']
        for encoding in encodings:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode text file with any known encoding")
    
    async def _parse_pdf(self, content: bytes) -> str:
        """Parse PDF file using PyPDF2"""
        try:
            import PyPDF2
            
            pdf_file = BytesIO(content)
            reader = PyPDF2.PdfReader(pdf_file)
            
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"PDF parsing error: {e}")
            raise ValueError(f"Failed to parse PDF: {e}")
    
    async def _parse_docx(self, content: bytes) -> str:
        """Parse DOCX file using python-docx"""
        try:
            from docx import Document
            
            docx_file = BytesIO(content)
            doc = Document(docx_file)
            
            text_parts = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"DOCX parsing error: {e}")
            raise ValueError(f"Failed to parse DOCX: {e}")
    
    # ========================================
    # Text Chunking
    # ========================================
    
    def chunk_text(
        self, 
        text: str, 
        chunk_size: int = CHUNK_SIZE, 
        overlap: int = CHUNK_OVERLAP
    ) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks.
        
        Uses sentence-aware splitting to avoid breaking mid-sentence.
        
        Args:
            text: Full document text
            chunk_size: Target chunk size in tokens (approx)
            overlap: Overlap between chunks in tokens
            
        Returns:
            List of chunk dicts with content and metadata
        """
        # Simple tokenization approximation: 1 token ≈ 4 characters
        char_chunk_size = chunk_size * 4
        char_overlap = overlap * 4
        
        # Clean and normalize text
        text = text.strip()
        text = ' '.join(text.split())  # Normalize whitespace
        
        if len(text) <= char_chunk_size:
            return [{
                'content': text,
                'chunk_index': 0,
                'token_count': len(text) // 4
            }]
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = start + char_chunk_size
            
            # If not at the end, try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending punctuation
                for punct in ['. ', '.\n', '? ', '!\n', '\n\n']:
                    last_punct = text[start:end].rfind(punct)
                    if last_punct > char_chunk_size * 0.5:  # At least 50% of chunk
                        end = start + last_punct + len(punct)
                        break
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    'content': chunk_text,
                    'chunk_index': chunk_index,
                    'token_count': len(chunk_text) // 4
                })
                chunk_index += 1
            
            # Move start with overlap
            start = end - char_overlap
            if start >= len(text) - char_overlap:
                break
        
        return chunks
    
    # ========================================
    # OpenAI Embeddings
    # ========================================
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding vector for text using OpenAI API.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector (1536 dimensions for text-embedding-3-small)
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": EMBEDDING_MODEL,
                    "input": text[:8000],  # Limit input length
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"OpenAI embedding error: {response.text}")
                raise ValueError(f"Embedding API error: {response.status_code}")
            
            data = response.json()
            return data["data"][0]["embedding"]
    
    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts in batch.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        # OpenAI supports batch embedding
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": EMBEDDING_MODEL,
                    "input": [t[:8000] for t in texts],  # Limit input length
                },
                timeout=60.0
            )
            
            if response.status_code != 200:
                logger.error(f"OpenAI embedding error: {response.text}")
                raise ValueError(f"Embedding API error: {response.status_code}")
            
            data = response.json()
            # Sort by index to ensure correct order
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in sorted_data]
    
    # ========================================
    # Database Operations
    # ========================================
    
    async def store_chunks_with_embeddings(
        self,
        document_id: int,
        agent_id: int,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> int:
        """
        Store chunks with their embeddings in PostgreSQL.
        
        Args:
            document_id: Parent document ID
            agent_id: Agent ID for fast lookup
            chunks: List of chunk dicts
            embeddings: Corresponding embedding vectors
            
        Returns:
            Number of chunks stored
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Chunks and embeddings count mismatch")
        
        for chunk, embedding in zip(chunks, embeddings):
            # Convert embedding to PostgreSQL vector format
            embedding_str = f"[{','.join(map(str, embedding))}]"
            
            await self.db.execute(
                text("""
                    INSERT INTO document_chunks 
                    (document_id, agent_id, content, chunk_index, token_count, embedding, created_at)
                    VALUES (:doc_id, :agent_id, :content, :chunk_idx, :tokens, :embedding::vector, NOW())
                """),
                {
                    "doc_id": document_id,
                    "agent_id": agent_id,
                    "content": chunk["content"],
                    "chunk_idx": chunk["chunk_index"],
                    "tokens": chunk["token_count"],
                    "embedding": embedding_str
                }
            )
        
        await self.db.commit()
        return len(chunks)
    
    async def semantic_search(
        self,
        agent_id: int,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search across agent's documents.
        
        Args:
            agent_id: Agent to search within
            query: Search query
            limit: Max results to return
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of matching chunks with scores
        """
        # Get query embedding
        query_embedding = await self.get_embedding(query)
        embedding_str = f"[{','.join(map(str, query_embedding))}]"
        
        # Search using cosine similarity
        result = await self.db.execute(
            text("""
                SELECT 
                    dc.id,
                    dc.content,
                    dc.chunk_index,
                    ad.filename,
                    1 - (dc.embedding <=> :query_embedding::vector) as similarity
                FROM document_chunks dc
                JOIN agent_documents ad ON dc.document_id = ad.id
                WHERE dc.agent_id = :agent_id
                AND 1 - (dc.embedding <=> :query_embedding::vector) > :threshold
                ORDER BY dc.embedding <=> :query_embedding::vector
                LIMIT :limit
            """),
            {
                "agent_id": agent_id,
                "query_embedding": embedding_str,
                "threshold": similarity_threshold,
                "limit": limit
            }
        )
        
        rows = result.fetchall()
        return [
            {
                "id": row[0],
                "content": row[1],
                "chunk_index": row[2],
                "document_filename": row[3],
                "score": float(row[4])
            }
            for row in rows
        ]
    
    # ========================================
    # Full Processing Pipeline
    # ========================================
    
    async def process_document(
        self,
        document_id: int,
        agent_id: int,
        file_content: bytes,
        file_type: str
    ) -> Tuple[int, int]:
        """
        Full document processing pipeline.
        
        1. Parse document
        2. Chunk text
        3. Generate embeddings
        4. Store in database
        
        Args:
            document_id: Document record ID
            agent_id: Owner agent ID
            file_content: Raw file bytes
            file_type: File extension
            
        Returns:
            Tuple of (chunk_count, token_count)
        """
        try:
            # 1. Parse document
            logger.info(f"Parsing document {document_id} ({file_type})")
            text = await self.parse_document(file_content, file_type)
            
            if not text.strip():
                raise ValueError("Document is empty or could not be parsed")
            
            # 2. Chunk text
            logger.info(f"Chunking document {document_id}")
            chunks = self.chunk_text(text)
            
            if not chunks:
                raise ValueError("No chunks created from document")
            
            # 3. Generate embeddings (in batches of 100)
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            all_embeddings = []
            batch_size = 100
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                batch_texts = [c["content"] for c in batch]
                batch_embeddings = await self.get_embeddings_batch(batch_texts)
                all_embeddings.extend(batch_embeddings)
            
            # 4. Store chunks with embeddings
            logger.info(f"Storing chunks for document {document_id}")
            await self.store_chunks_with_embeddings(
                document_id, agent_id, chunks, all_embeddings
            )
            
            total_tokens = sum(c["token_count"] for c in chunks)
            return len(chunks), total_tokens
            
        except Exception as e:
            logger.error(f"Document processing error: {e}")
            raise
