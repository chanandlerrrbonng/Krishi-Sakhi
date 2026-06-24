"""
Shared RAG logic for the Ask-It notebook and Streamlit chat UI.
Configure via environment variables (see README).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from openai import OpenAI
from qdrant_client import QdrantClient


def _payload_as_dict(payload: Any) -> dict:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return dict(payload)


@dataclass
class RAGConfig:
    collection_name: str
    embedding_model: str
    chat_model: str
    embed_batch_size: int


def load_config() -> RAGConfig:
    return RAGConfig(
        collection_name=os.environ.get("COLLECTION_NAME", "knowledge_base_rag"),
        embedding_model=os.environ.get("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B"),
        chat_model=os.environ.get("CHAT_MODEL", "openai/gpt-oss-120b"),
        embed_batch_size=int(os.environ.get("EMBED_BATCH_SIZE", "32")),
    )


def build_qdrant_client() -> QdrantClient:
    path = os.environ.get("QDRANT_PATH", "").strip()
    if path:
        return QdrantClient(path=path)
    url = os.environ.get("QDRANT_URL", "<VAYU_QDRANT_URL>").strip()
    if not url:
        raise ValueError(
            "Set QDRANT_URL (and QDRANT_API_KEY) for hosted Qdrant, or QDRANT_PATH for local on-disk mode."
        )
    api_key = os.environ.get("QDRANT_API_KEY", "<VAYU_QDRANT_API_KEY>").strip() or None
    port = int(os.environ.get("QDRANT_PORT", "443"))
    return QdrantClient(
        url=url,
        api_key=api_key,
        port=port,
    )


def build_openai_client(is_embedding: bool = False) -> OpenAI:
    env_var = "EMBEDDING_OPENAI_API_KEY" if is_embedding else "LLM_OPENAI_API_KEY"
    api_key = os.environ.get(env_var, "sk-**********************").strip() or None
    base_url = os.environ.get("OPENAI_BASE_URL", "<VAYU_MODEL_AS_A_SERVICE_URL>").strip() or None
    kwargs: dict = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)

class RAGEngine:
    """Query-time RAG: embed question, search Qdrant, call chat model with context."""

    def __init__(self) -> None:
        self._cfg = load_config()
        self._qdrant = build_qdrant_client()
        self._embedding_openai = build_openai_client(is_embedding=True)
        self._chat_openai = build_openai_client(is_embedding=False)

    @property
    def config(self) -> RAGConfig:
        return self._cfg

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        out: list[list[float]] = []
        bs = self._cfg.embed_batch_size
        for i in range(0, len(texts), bs):
            batch = texts[i : i + bs]
            res = self._embedding_openai.embeddings.create(
                input=batch,
                model=self._cfg.embedding_model,
            )
            out.extend(d.embedding for d in res.data)
        return out

    def retrieve(self, question: str, limit: int) -> list[Any]:
        qvec = self.embed_texts([question])[0]
        if hasattr(self._qdrant, "query_points"):
            res = self._qdrant.query_points(
                collection_name=self._cfg.collection_name,
                query=qvec,
                limit=limit,
                with_payload=True,
            )
            return list(res.points)
        return self._qdrant.search(
            collection_name=self._cfg.collection_name,
            query_vector=qvec,
            limit=limit,
        )

    def ask(self, question: str, top_k: int = 4) -> tuple[str, list[dict]]:
        hits = self.retrieve(question, limit=top_k)
        blocks: list[str] = []
        sources: list[dict] = []
        for h in hits:
            pl = _payload_as_dict(getattr(h, "payload", None))
            if not pl:
                continue
            src = pl.get("source", "") or ""
            body = pl.get("text", "") or ""
            score = getattr(h, "score", None)
            sources.append(
                {
                    "source": src,
                    "text": (body[:1200] + "…") if len(body) > 1200 else body,
                    "score": float(score) if score is not None else None,
                }
            )
            blocks.append(f"[{src}]\n{body}" if src else body)
        context = "\n\n---\n\n".join(blocks)
        if not context.strip():
            return (
                "No matching passages were found in the vector database. "
                "Run ingestion (e.g. `qna.ipynb`) so the collection has data.",
                [],
            )

        system = (
            "You are a helpful assistant. Answer using only the provided context. "
            "If the context is insufficient, say you do not know. "
            "Mention which source file the answer came from when possible."
        )
        user_msg = f"Context:\n{context}\n\nQuestion: {question}"
        completion = self._chat_openai.chat.completions.create(
            model=self._cfg.chat_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )
        answer = (completion.choices[0].message.content or "").strip()
        return answer, sources
