
# vector_db/retriever.py
"""Document retriever for RAG"""
import logging
from typing import List, Dict
from .store import VectorStore

logger = logging.getLogger(__name__)

class DocumentRetriever:
    """Retrieves relevant documents for RAG"""
    
    def __init__(self):
        self.vector_store = VectorStore()
    
    def retrieve_context(
        self,
        query: str,
        k: int = 4
    ) -> Dict[str, any]:
        """
        Retrieve relevant context for a query
        
        Args:
            query: User query
            k: Number of documents to retrieve
            
        Returns:
            Dictionary with context and sources
        """
        try:
            # Search for relevant documents
            results = self.vector_store.search(query, k=k)
            
            if not results:
                return {
                    "context": "No relevant information found.",
                    "sources": []
                }
            
            # Build context from results
            context_parts = []
            sources = []
            
            for i, doc in enumerate(results, 1):
                context_parts.append(f"[{i}] {doc.page_content}")
                
                # Extract source info
                source = {
                    "title": doc.metadata.get("source", "Unknown"),
                    "url": doc.metadata.get("url", "#"),
                    "content": doc.page_content[:200] + "..."
                }
                sources.append(source)
            
            context = "\n\n".join(context_parts)
            
            return {
                "context": context,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return {
                "context": "Error retrieving information.",
                "sources": []
            }
    
    def get_vector_store(self) -> VectorStore:
        """Get the underlying vector store"""
        return self.vector_store