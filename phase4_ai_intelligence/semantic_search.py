"""
Semantic Search & RAG (Retrieval-Augmented Generation)
=======================================================

Uses dense embeddings for semantic similarity search against knowledge base.
Enables retrieval-augmented generation for context-aware responses.

Features:
- Embedding-based semantic search
- Dense vector retrieval
- Knowledge base indexing
- Similarity scoring
- Batch processing
- Cosine similarity optimization

Best Models:
- sentence-transformers/all-MiniLM-L6-v2 (lightweight, 22M params)
- sentence-transformers/all-mpnet-base-v2 (accurate, 109M params)
- BAAI/bge-small-en (competitive accuracy)
"""

import os
import json
import logging
import pickle
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import time

try:
    from sentence_transformers import SentenceTransformer, util
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from semantic search."""
    document: str
    query: str
    similarity_score: float
    rank: int
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "document": self.document[:200],  # Truncate for display
            "similarity": round(self.similarity_score, 4),
            "rank": self.rank,
            "metadata": self.metadata or {}
        }


@dataclass
class IndexedDocument:
    """Document with cached embedding."""
    text: str
    embedding: np.ndarray
    metadata: Dict
    id: str
    indexed_at: float


class SemanticSearchEngine:
    """
    Production-grade semantic search using embeddings.
    
    Enables RAG with dense vector retrieval for knowledge-grounded responses.
    """
    
    # Best embedding models
    EMBEDDING_MODELS = {
        "minilm": "sentence-transformers/all-MiniLM-L6-v2",        # 22M params, fast
        "mpnet": "sentence-transformers/all-mpnet-base-v2",        # 109M params, accurate
        "bge": "BAAI/bge-small-en",                                # 33M params, competitive
        "distiluse": "distiluse-base-multilingual-cased-v2",       # Multilingual
    }
    
    def __init__(self, model_name: str = "minilm", cache_dir: str = "models/cache",
                 device: str = "cpu"):
        """
        Initialize semantic search engine.
        
        Args:
            model_name: Embedding model (minilm, mpnet, bge, distiluse)
            cache_dir: Cache directory
            device: Device (cpu, cuda)
        """
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.device = device
        self.model = None
        self.documents: Dict[str, IndexedDocument] = {}
        self.embeddings: Dict[str, np.ndarray] = {}
        self.index_file = os.path.join(cache_dir, "semantic_index.pkl")
        
        os.makedirs(cache_dir, exist_ok=True)
        
        if HAS_SENTENCE_TRANSFORMERS:
            self._load_model()
            self._load_index()
        else:
            logger.warning("sentence-transformers not installed")
    
    def _load_model(self):
        """Load embedding model."""
        try:
            model_id = self.EMBEDDING_MODELS.get(self.model_name, 
                                                 self.EMBEDDING_MODELS["minilm"])
            logger.info(f"Loading embedding model: {model_id}")
            
            self.model = SentenceTransformer(model_id, device=self.device)
            
            logger.info(f"Embedding model loaded: {model_id}")
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.model = None
    
    def _load_index(self):
        """Load cached embeddings index."""
        try:
            if os.path.exists(self.index_file):
                with open(self.index_file, 'rb') as f:
                    index_data = pickle.load(f)
                    self.documents = index_data.get('documents', {})
                    self.embeddings = index_data.get('embeddings', {})
                    logger.info(f"Loaded {len(self.documents)} documents from index")
        except Exception as e:
            logger.warning(f"Failed to load index: {e}")
    
    def _save_index(self):
        """Save embeddings index."""
        try:
            with open(self.index_file, 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'embeddings': self.embeddings,
                }, f)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    def index_documents(self, documents: List[str], 
                       metadata: Optional[List[Dict]] = None,
                       batch_size: int = 32) -> Dict:
        """
        Index documents for semantic search.
        
        Args:
            documents: List of document texts
            metadata: Optional metadata for each document
            batch_size: Batch size for embedding
            
        Returns:
            Indexing statistics
        """
        if self.model is None:
            logger.error("Model not loaded, cannot index documents")
            return {"error": "model_not_loaded"}
        
        if not documents:
            return {"indexed": 0, "error": "empty_documents"}
        
        try:
            start_time = time.time()
            
            # Generate embeddings in batches
            embeddings = self.model.encode(
                documents,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=True
            )
            
            # Store indexed documents
            for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                doc_id = f"doc_{len(self.documents)}_{int(time.time())}"
                doc_metadata = metadata[i] if metadata and i < len(metadata) else {}
                
                self.documents[doc_id] = IndexedDocument(
                    text=doc,
                    embedding=embedding,
                    metadata=doc_metadata,
                    id=doc_id,
                    indexed_at=time.time()
                )
                
                self.embeddings[doc_id] = embedding
            
            # Save index
            self._save_index()
            
            elapsed_time = time.time() - start_time
            
            return {
                "indexed": len(documents),
                "total_documents": len(self.documents),
                "embedding_dim": embeddings[0].shape[0],
                "time_seconds": round(elapsed_time, 2),
                "docs_per_second": round(len(documents) / elapsed_time, 1),
            }
            
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            return {"error": str(e)}
    
    def search(self, query: str, top_k: int = 5, 
               threshold: float = 0.3) -> List[SearchResult]:
        """
        Search for semantically similar documents.
        
        Args:
            query: Query text
            top_k: Number of results to return
            threshold: Minimum similarity score
            
        Returns:
            List of SearchResult objects
        """
        if self.model is None or not self.documents:
            logger.warning("Model or documents not available for search")
            return []
        
        try:
            # Encode query
            query_embedding = self.model.encode(query, convert_to_numpy=True)
            
            # Compute similarities
            results = []
            for doc_id, indexed_doc in self.documents.items():
                # Cosine similarity
                similarity = np.dot(query_embedding, indexed_doc.embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(indexed_doc.embedding)
                )
                
                if similarity >= threshold:
                    results.append((similarity, doc_id, indexed_doc))
            
            # Sort by similarity
            results.sort(key=lambda x: x[0], reverse=True)
            
            # Create search results
            search_results = []
            for rank, (similarity, doc_id, indexed_doc) in enumerate(results[:top_k]):
                search_results.append(SearchResult(
                    document=indexed_doc.text,
                    query=query,
                    similarity_score=similarity,
                    rank=rank + 1,
                    metadata=indexed_doc.metadata
                ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def semantic_similarity(self, text1: str, text2: str) -> float:
        """Get semantic similarity between two texts."""
        if self.model is None:
            return 0.0
        
        try:
            embeddings = self.model.encode([text1, text2], convert_to_numpy=True)
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            return float(similarity)
        except Exception as e:
            logger.error(f"Similarity computation failed: {e}")
            return 0.0
    
    def get_document(self, doc_id: str) -> Optional[IndexedDocument]:
        """Get document by ID."""
        return self.documents.get(doc_id)
    
    def get_statistics(self) -> Dict:
        """Get index statistics."""
        if not self.documents:
            return {
                "total_documents": 0,
                "index_size_kb": 0,
                "embedding_dimension": 0
            }
        
        first_embedding = next(iter(self.embeddings.values()))
        embedding_size_bytes = first_embedding.nbytes * len(self.embeddings)
        
        return {
            "total_documents": len(self.documents),
            "index_size_mb": round(embedding_size_bytes / (1024 * 1024), 2),
            "embedding_dimension": len(first_embedding),
            "model_name": self.model_name,
            "device": self.device,
        }
    
    def clear_index(self):
        """Clear all indexed documents."""
        self.documents.clear()
        self.embeddings.clear()
        self._save_index()
        logger.info("Index cleared")


class RAGSystem:
    """
    RAG (Retrieval-Augmented Generation) system combining
    semantic search with LLM response generation.
    """
    
    def __init__(self, search_engine: SemanticSearchEngine):
        """Initialize RAG system."""
        self.search_engine = search_engine
    
    def generate_context(self, query: str, top_k: int = 3) -> str:
        """
        Generate context from retrieved documents.
        
        Args:
            query: User query
            top_k: Number of documents to retrieve
            
        Returns:
            Formatted context string
        """
        results = self.search_engine.search(query, top_k=top_k)
        
        if not results:
            return "No relevant documents found."
        
        context_parts = []
        for result in results:
            context_parts.append(
                f"[Source #{result.rank}, Confidence: {result.similarity_score:.2%}]\n"
                f"{result.document}\n"
            )
        
        return "\n".join(context_parts)
    
    def generate_prompt(self, query: str, system_prompt: str = "") -> str:
        """
        Generate RAG-enhanced prompt for LLM.
        
        Args:
            query: User query
            system_prompt: Optional system prompt
            
        Returns:
            Complete prompt with context
        """
        context = self.generate_context(query)
        
        prompt = f"""{system_prompt}

Context from Knowledge Base:
{context}

User Query:
{query}

Please provide a helpful response based on the context above.
If the context is not relevant, you may answer based on your general knowledge."""
        
        return prompt.strip()
