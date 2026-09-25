"""
AUTOSAR HLD AI - FAISS Vector Store
Persistent FAISS-based vector database for embedding storage and retrieval.
"""

import json
import os
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from app.utils.config import settings
from app.utils.logger import logger


@dataclass
class SearchResult:
    """A single search result with metadata."""
    chunk_id: str
    text: str
    score: float
    metadata: Dict


class FAISSStore:
    """
    FAISS-based vector store with persistent storage.
    Stores embeddings, text, and metadata separately.
    """

    def __init__(self, store_path: Optional[str] = None, dimension: int = None):
        """
        Initialize the FAISS store.

        Args:
            store_path: Directory for persistent storage
            dimension: Embedding dimension
        """
        self.store_path = Path(store_path or settings.VECTOR_STORE_PATH)
        self.dimension = dimension or settings.EMBEDDING_DIMENSION
        self.index = None
        self.metadata_store: List[Dict] = []
        self.texts: List[str] = []
        self._faiss = None
        self._initialized = False

    def _import_faiss(self):
        """Lazy import of FAISS."""
        if self._faiss is None:
            try:
                import faiss
                self._faiss = faiss
            except ImportError:
                logger.error("FAISS not installed. Run: pip install faiss-cpu")
                raise ImportError("faiss-cpu is required. Install with: pip install faiss-cpu")
        return self._faiss

    def initialize(self) -> bool:
        """Initialize or load existing FAISS index."""
        try:
            faiss = self._import_faiss()
            index_path = self.store_path / "faiss_index.bin"
            meta_path = self.store_path / "metadata.json"
            texts_path = self.store_path / "texts.json"

            self.store_path.mkdir(parents=True, exist_ok=True)

            if index_path.exists() and meta_path.exists():
                # Load existing index
                self.index = faiss.read_index(str(index_path))
                with open(meta_path, 'r', encoding='utf-8') as f:
                    self.metadata_store = json.load(f)
                if texts_path.exists():
                    with open(texts_path, 'r', encoding='utf-8') as f:
                        self.texts = json.load(f)
                self.dimension = self.index.d
                logger.info(
                    f"Loaded FAISS index: {self.index.ntotal} vectors, "
                    f"dimension: {self.dimension}"
                )
            else:
                # Create new index
                self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for normalized vectors
                self.metadata_store = []
                self.texts = []
                logger.info(f"Created new FAISS index, dimension: {self.dimension}")

            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"FAISS initialization failed: {e}")
            return False

    @property
    def is_available(self) -> bool:
        return self._initialized and self.index is not None

    def add_vectors(
        self,
        embeddings: np.ndarray,
        texts: List[str],
        metadata_list: List[Dict]
    ) -> bool:
        """
        Add vectors with their texts and metadata.

        Args:
            embeddings: Numpy array of shape (n, dimension)
            texts: List of text strings
            metadata_list: List of metadata dicts

        Returns:
            True if successful
        """
        if not self.is_available:
            if not self.initialize():
                return False

        try:
            if len(embeddings) == 0:
                return True

            # Ensure correct shape and type
            if len(embeddings.shape) == 1:
                embeddings = embeddings.reshape(1, -1)
            embeddings = embeddings.astype(np.float32)

            # Update dimension if needed
            if self.index.d != embeddings.shape[1]:
                faiss = self._import_faiss()
                self.index = faiss.IndexFlatIP(embeddings.shape[1])
                self.dimension = embeddings.shape[1]

            self.index.add(embeddings)
            self.texts.extend(texts)
            self.metadata_store.extend(metadata_list)

            logger.info(f"Added {len(embeddings)} vectors. Total: {self.index.ntotal}")
            return True
        except Exception as e:
            logger.error(f"Failed to add vectors: {e}")
            return False

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        document_id: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search for similar vectors.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            document_id: Optional filter by document

        Returns:
            List of SearchResult objects
        """
        if not self.is_available or self.index.ntotal == 0:
            return []

        try:
            if len(query_embedding.shape) == 1:
                query_embedding = query_embedding.reshape(1, -1)
            query_embedding = query_embedding.astype(np.float32)

            # Search more than needed if filtering by document
            search_k = top_k * 3 if document_id else top_k

            distances, indices = self.index.search(query_embedding, min(search_k, self.index.ntotal))

            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0 or idx >= len(self.metadata_store):
                    continue

                meta = self.metadata_store[idx]

                # Filter by document if specified
                if document_id and meta.get("document_id") != document_id:
                    continue

                text = self.texts[idx] if idx < len(self.texts) else ""

                results.append(SearchResult(
                    chunk_id=meta.get("chunk_id", ""),
                    text=text,
                    score=float(dist),
                    metadata=meta
                ))

                if len(results) >= top_k:
                    break

            return results
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")
            return []

    def save(self) -> bool:
        """Save index and metadata to disk."""
        if not self.is_available:
            return False

        try:
            faiss = self._import_faiss()
            self.store_path.mkdir(parents=True, exist_ok=True)

            index_path = self.store_path / "faiss_index.bin"
            meta_path = self.store_path / "metadata.json"
            texts_path = self.store_path / "texts.json"

            faiss.write_index(self.index, str(index_path))
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata_store, f, ensure_ascii=False)
            with open(texts_path, 'w', encoding='utf-8') as f:
                json.dump(self.texts, f, ensure_ascii=False)

            logger.info(f"FAISS store saved: {self.index.ntotal} vectors")
            return True
        except Exception as e:
            logger.error(f"Failed to save FAISS store: {e}")
            return False

    def delete_document(self, document_id: str) -> bool:
        """
        Remove all vectors for a specific document.
        Note: FAISS doesn't support deletion natively, so we rebuild.
        """
        if not self.is_available:
            return False

        try:
            faiss = self._import_faiss()

            # Find indices to keep
            keep_indices = [
                i for i, meta in enumerate(self.metadata_store)
                if meta.get("document_id") != document_id
            ]

            if len(keep_indices) == len(self.metadata_store):
                return True  # Nothing to delete

            # Reconstruct vectors for kept indices
            kept_vectors = []
            for idx in keep_indices:
                vec = self.index.reconstruct(idx)
                kept_vectors.append(vec)

            # Rebuild
            new_index = faiss.IndexFlatIP(self.dimension)
            new_texts = [self.texts[i] for i in keep_indices]
            new_metadata = [self.metadata_store[i] for i in keep_indices]

            if kept_vectors:
                vectors = np.array(kept_vectors, dtype=np.float32)
                new_index.add(vectors)

            self.index = new_index
            self.texts = new_texts
            self.metadata_store = new_metadata

            logger.info(f"Deleted document {document_id} from FAISS. Remaining: {self.index.ntotal}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document from FAISS: {e}")
            return False

    def get_stats(self) -> Dict:
        """Get vector store statistics."""
        return {
            "total_vectors": self.index.ntotal if self.index else 0,
            "dimension": self.dimension,
            "store_path": str(self.store_path),
            "initialized": self._initialized
        }


# Global singleton
_faiss_store: Optional[FAISSStore] = None


def get_faiss_store() -> FAISSStore:
    """Get or create the global FAISS store instance."""
    global _faiss_store
    if _faiss_store is None:
        _faiss_store = FAISSStore()
    return _faiss_store
