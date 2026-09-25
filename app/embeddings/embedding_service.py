"""
AUTOSAR HLD AI - Embedding Service
Generates embeddings using sentence-transformers.
Configurable model with BGE/E5 support.
"""

import numpy as np
from typing import List, Optional
from app.utils.config import settings
from app.utils.logger import logger


class EmbeddingService:
    """
    Embedding generation service using sentence-transformers.
    Supports configurable models including BGE and E5 families.
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the embedding service.

        Args:
            model_name: Override the configured model name
        """
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.model = None
        self.dimension = settings.EMBEDDING_DIMENSION
        self._initialized = False

    def initialize(self) -> bool:
        """
        Load the embedding model. Separated from __init__ to allow lazy loading.

        Returns:
            True if model loaded successfully
        """
        if self._initialized:
            return True

        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            self._initialized = True
            logger.info(
                f"Embedding model loaded: {self.model_name} "
                f"(dimension: {self.dimension})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self._initialized = False
            return False

    @property
    def is_available(self) -> bool:
        """Check if embedding service is ready."""
        return self._initialized and self.model is not None

    def embed_text(self, text: str) -> Optional[np.ndarray]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding vector as numpy array
        """
        if not self.is_available:
            if not self.initialize():
                return None

        try:
            # BGE models benefit from a query prefix
            if "bge" in self.model_name.lower():
                text = f"Represent this sentence: {text}"

            embedding = self.model.encode(text, normalize_embeddings=True)
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> Optional[np.ndarray]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts
            batch_size: Batch size for processing

        Returns:
            Array of embedding vectors
        """
        if not self.is_available:
            if not self.initialize():
                return None

        try:
            # Add prefix for BGE models
            if "bge" in self.model_name.lower():
                texts = [f"Represent this sentence: {t}" for t in texts]

            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=len(texts) > 50
            )
            return np.array(embeddings, dtype=np.float32)
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            return None

    def embed_query(self, query: str) -> Optional[np.ndarray]:
        """
        Generate embedding for a search query.
        Uses query-specific prefix for BGE models.

        Args:
            query: Search query text

        Returns:
            Query embedding vector
        """
        if not self.is_available:
            if not self.initialize():
                return None

        try:
            # BGE models use a different prefix for queries
            if "bge" in self.model_name.lower():
                query = f"Represent this sentence for searching relevant passages: {query}"

            embedding = self.model.encode(query, normalize_embeddings=True)
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            logger.error(f"Query embedding generation failed: {e}")
            return None


# Global singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
