"""
FactLoom Embedding Engine
Local sentence-transformers embedding provider running on CPU.
Zero external API key dependencies.
"""

import json
from typing import List, Union, Optional
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"

class EmbeddingEngine:
    _instance: Optional["EmbeddingEngine"] = None

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, device: Optional[str] = None):
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model = SentenceTransformer(model_name, device=self.device)

    @classmethod
    def get_instance(cls, model_name: str = DEFAULT_MODEL_NAME, device: Optional[str] = None) -> "EmbeddingEngine":
        if cls._instance is None or cls._instance.model_name != model_name:
            cls._instance = cls(model_name, device=device)
        return cls._instance

    def embed_text(self, text: str) -> np.ndarray:
        """
        Embed a single text string into a normalized 1D float32 numpy vector.
        """
        cleaned = text.strip() if text else ""
        if not cleaned:
            return np.zeros(384, dtype=np.float32)
        vec = self._model.encode(cleaned, convert_to_numpy=True, normalize_embeddings=True)
        return vec.astype(np.float32)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Embed a list of text strings into normalized float32 vectors.
        """
        if not texts:
            return np.empty((0, 384), dtype=np.float32)
        vecs = self._model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return vecs.astype(np.float32)

    @staticmethod
    def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        Compute cosine similarity between two unit-normalized vectors.
        """
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    @staticmethod
    def serialize_vector(vec: np.ndarray) -> bytes:
        """Serialize float32 numpy vector into bytes for SQLite BLOB storage."""
        return vec.astype(np.float32).tobytes()

    @staticmethod
    def deserialize_vector(data: Union[bytes, str, memoryview]) -> np.ndarray:
        """Deserialize bytes or JSON back into float32 numpy vector."""
        if isinstance(data, memoryview):
            data = data.tobytes()
        if isinstance(data, bytes):
            return np.frombuffer(data, dtype=np.float32)
        if isinstance(data, str):
            arr = json.loads(data)
            return np.array(arr, dtype=np.float32)
        raise ValueError(f"Unsupported vector data format: {type(data)}")
