
# vector_db/store.py
"""Vector store implementation using ChromaDB"""
import logging
from pathlib import Path
from typing import List, Optional
from langchain.schema import Document
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config import get_config
from .embeddings import get_embeddings

logger = logging.getLogger(__name__)

class VectorStore:
    """Vector store for document storage and retrieval"""
    
    def __init__(self):
        self.config = get_config()
        self.embeddings = get_embeddings()
        self.persist_directory = self.config.vector_db.persist_directory
        
        # Create persist directory if it doesn't exist
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB
        self.vectordb = Chroma(
            collection_name=self.config.vector_db.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.vector_db.chunking.chunk_size,
            chunk_overlap=self.config.vector_db.chunking.chunk_overlap,
            separators=self.config.vector_db.chunking.separators
        )
        
        logger.info(f"Vector store initialized: {self.persist_directory}")
    
    def add_documents(self, documents: List[Document]) -> int:
        """
        Add documents to the vector store
        
        Args:
            documents: List of Document objects
            
        Returns:
            Number of chunks added
        """
        if not documents:
            return 0
        
        try:
            # Split documents into chunks
            chunks = self.text_splitter.split_documents(documents)
            
            # Add to vector store
            self.vectordb.add_documents(chunks)
            
            logger.info(f"Added {len(chunks)} chunks from {len(documents)} documents")
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return 0
    
    def search(
        self,
        query: str,
        k: Optional[int] = None,
        filter: Optional[dict] = None
    ) -> List[Document]:
        """
        Search for relevant documents
        
        Args:
            query: Search query
            k: Number of results to return
            filter: Optional metadata filter
            
        Returns:
            List of relevant documents
        """
        k = k or self.config.vector_db.search.k
        
        try:
            results = self.vectordb.similarity_search(
                query=query,
                k=k,
                filter=filter
            )
            return results
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def search_with_score(
        self,
        query: str,
        k: Optional[int] = None,
        score_threshold: Optional[float] = None
    ) -> List[tuple[Document, float]]:
        """
        Search with relevance scores
        
        Args:
            query: Search query
            k: Number of results
            score_threshold: Minimum relevance score
            
        Returns:
            List of (document, score) tuples
        """
        k = k or self.config.vector_db.search.k
        score_threshold = score_threshold or self.config.vector_db.search.score_threshold
        
        try:
            results = self.vectordb.similarity_search_with_score(
                query=query,
                k=k
            )
            
            # Filter by score threshold
            filtered = [
                (doc, score) for doc, score in results
                if score >= score_threshold
            ]
            
            return filtered
        except Exception as e:
            logger.error(f"Search with score error: {e}")
            return []
    
    def delete_collection(self) -> None:
        """Delete the entire collection"""
        try:
            self.vectordb.delete_collection()
            logger.info("Collection deleted")
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
    
    def get_document_count(self) -> int:
        """Get number of documents in the collection"""
        try:
            return self.vectordb._collection.count()
        except:
            return 0

