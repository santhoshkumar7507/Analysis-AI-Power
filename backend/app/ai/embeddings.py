"""Provider-independent embedding generation engine with deterministic local fallback."""

import math
import hashlib
from typing import List
import httpx
from app.core.config import settings

VECTOR_DIMENSION = 384


class EmbeddingEngine:
    @classmethod
    def get_embedding(cls, text: str) -> List[float]:
        """Generate a normalized dense vector embedding for a given text."""
        cleaned_text = text.strip()
        if not cleaned_text:
            return [0.0] * VECTOR_DIMENSION

        if settings.AI_PROVIDER == "openai" and settings.OPENAI_API_KEY:
            try:
                return cls._get_openai_embedding(cleaned_text)
            except Exception:
                # Fallback to deterministic semantic vector if OpenAI API fails or times out
                return cls._get_deterministic_embedding(cleaned_text)

        return cls._get_deterministic_embedding(cleaned_text)

    @classmethod
    def _get_openai_embedding(cls, text: str) -> List[float]:
        """Fetch real embedding from OpenAI API."""
        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": text,
            "model": settings.EMBEDDING_MODEL_NAME,
        }
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            # Return first embedding
            return data["data"][0]["embedding"][:VECTOR_DIMENSION]

    @staticmethod
    def _get_deterministic_embedding(text: str) -> List[float]:
        """Generate a reproducible, normalized semantic vector using deterministic n-gram hashing."""
        vector = [0.0] * VECTOR_DIMENSION
        tokens = text.lower().split()

        # Semantic keywords mapping for domain alignment in support scenarios
        semantic_buckets = {
            "refund": 10, "charge": 11, "billing": 12, "invoice": 13, "money": 14, "payment": 15, "subscription": 16,
            "error": 50, "timeout": 51, "api": 52, "504": 53, "500": 54, "server": 55, "crash": 56, "database": 57,
            "password": 90, "sso": 91, "saml": 92, "login": 93, "auth": 94, "lockout": 95, "2fa": 96, "token": 97,
            "shipment": 140, "order": 141, "tracking": 142, "delivery": 143, "fedex": 144, "package": 145,
            "policy": 200, "sla": 201, "deadline": 202, "escalation": 203, "guideline": 204,
        }

        # Boost semantic buckets based on domain vocabulary
        for token in tokens:
            cleaned_token = token.strip(".,!?:;\"'()[]{}")
            for keyword, bucket_idx in semantic_buckets.items():
                if keyword in cleaned_token:
                    vector[bucket_idx] += 3.5

            # Hash token character tri-grams to distribute across the 384 dimensions
            if len(cleaned_token) >= 3:
                for i in range(len(cleaned_token) - 2):
                    trigram = cleaned_token[i:i+3]
                    h = int(hashlib.md5(trigram.encode("utf-8")).hexdigest(), 16)
                    idx = h % VECTOR_DIMENSION
                    weight = 1.0 if (h % 2 == 0) else -1.0
                    vector[idx] += weight
            else:
                h = int(hashlib.md5(cleaned_token.encode("utf-8")).hexdigest(), 16)
                idx = h % VECTOR_DIMENSION
                vector[idx] += 1.0

        # L2-normalize vector to unit length so dot product equals cosine similarity
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            return [v / norm for v in vector]
        return vector

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity between two float vectors."""
        if len(v1) != len(v2) or not v1 or not v2:
            return 0.0
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return max(0.0, min(1.0, dot_product / (norm1 * norm2)))
