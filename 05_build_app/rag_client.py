"""
Krishi-Sakhi — shared RAG logic for the Streamlit chat UI and deployment.
Mirrors qna.ipynb. README.md is the single source of truth.

README §6  — hard constraints (client-side hybrid, manual query prefix, no query_points)
README §7B/§7C/§7D/§7E — embeddings, hybrid retrieval, citations, grounded prompt
"""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi

_REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_REPO_ROOT / ".env", override=True)

# ---- README §6 Corr. 2 / §7B — Qwen3 query-instruction prefix (query path only, English) ----
QWEN_INSTRUCT = "Instruct: Given a question, retrieve passages that answer it\nQuery:"

# ---- README §7C — hybrid retrieval constants ----
DENSE_TOP_K = 20
BM25_TOP_K = 20
RRF_FUSE_TOP_K = 12
RRF_K = 60
ANSWER_TOP_K = 4  # README S1 pipeline tail; reranker slots in front of this later.

# ---- README §7E — grounded-answer prompt config ----
CHAT_TEMPERATURE = 0.0
CHAT_TEMPERATURE_FALLBACK = 0.1
REFUSAL_STRING = "I could not find this in the provided documents."


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise EnvironmentError(
            f"Missing required environment variable {name!r}. "
            f"Set it in ask-it/.env (copy from .env.example)."
        )
    if "<VAYU_" in value or "<YOUR_" in value or "<COLLECTION" in value or "***" in value:
        raise EnvironmentError(
            f"Environment variable {name!r} still contains a placeholder value."
        )
    return value


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
        collection_name=os.environ.get("COLLECTION_NAME", "").strip() or "knowledge_base_rag",
        embedding_model=os.environ.get("EMBEDDING_MODEL", "").strip() or "Qwen/Qwen3-Embedding-8B",
        chat_model=os.environ.get("CHAT_MODEL", "").strip() or "openai/gpt-oss-120b",
        embed_batch_size=int(os.environ.get("EMBED_BATCH_SIZE", "").strip() or "32"),
    )


def build_qdrant_client() -> QdrantClient:
    path = os.environ.get("QDRANT_PATH", "").strip()
    if path:
        return QdrantClient(path=path)
    url = _require_env("QDRANT_URL")
    api_key = _require_env("QDRANT_API_KEY")
    port = int(os.environ.get("QDRANT_PORT", "443"))
    return QdrantClient(url=url, api_key=api_key, port=port)


def build_openai_client(is_embedding: bool = False) -> OpenAI:
    env_var = "EMBEDDING_OPENAI_API_KEY" if is_embedding else "OPENAI_API_KEY"
    api_key = _require_env(env_var)
    base_url = _require_env("OPENAI_BASE_URL")
    return OpenAI(api_key=api_key, base_url=base_url)


class RAGEngine:
    """Query-time RAG: hybrid retrieve (dense + BM25 + RRF) → grounded, cited answer."""

    def __init__(self) -> None:
        self._cfg = load_config()
        self._qdrant = build_qdrant_client()
        self._embedding_openai = build_openai_client(is_embedding=True)
        self._chat_openai = build_openai_client(is_embedding=False)
        # README §7C — build BM25 ONCE at engine init (never rebuilt live).
        self._bm25: BM25Okapi | None = None
        self._bm25_payloads: list[dict] = []
        self._build_bm25_index()

    @property
    def config(self) -> RAGConfig:
        return self._cfg

    # ---- README §7B / §6 Corr. 2 — separate document vs. query embedding paths ----
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Documents — NO prefix."""
        if not texts:
            return []
        out: list[list[float]] = []
        bs = self._cfg.embed_batch_size
        for i in range(0, len(texts), bs):
            batch = texts[i : i + bs]
            try:
                res = self._embedding_openai.embeddings.create(
                    input=batch, model=self._cfg.embedding_model,
                )
            except Exception as e:
                raise RuntimeError(f"MaaS embedding call failed at batch {i}: {e}") from e
            out.extend(d.embedding for d in res.data)
        return out

    def embed_query(self, question: str) -> list[float]:
        """Query path only — manual English instruction prefix (no prompt_name to MaaS)."""
        return self.embed_texts([f"{QWEN_INSTRUCT}{question}"])[0]

    # ---- README §7C — client-side BM25 ----
    @staticmethod
    def _bm25_tokenize(text: str) -> list[str]:
        return text.split()

    def _build_bm25_index(self) -> None:
        payloads: list[dict] = []
        next_offset = None
        while True:
            records, next_offset = self._qdrant.scroll(
                collection_name=self._cfg.collection_name,
                with_payload=True,
                with_vectors=False,
                limit=256,
                offset=next_offset,
            )
            payloads.extend(_payload_as_dict(r.payload) for r in records if r.payload)
            if next_offset is None:
                break
        self._bm25_payloads = payloads
        if payloads:
            self._bm25 = BM25Okapi(
                [self._bm25_tokenize(p.get("text", "")) for p in payloads]
            )
        else:
            # Loud, not silent: the app should surface an empty collection clearly.
            self._bm25 = None
            print(
                f"WARNING: collection {self._cfg.collection_name!r} is empty — "
                "run ingestion (qna.ipynb) before querying."
            )

    def _dense_search(self, question: str, limit: int) -> list[dict]:
        qvec = self.embed_query(question)
        hits = self._qdrant.search(
            collection_name=self._cfg.collection_name,
            query_vector=qvec,
            limit=limit,
            with_payload=True,
        )
        return [_payload_as_dict(h.payload) for h in hits if h.payload]

    def _bm25_search(self, question: str, limit: int) -> list[dict]:
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(self._bm25_tokenize(question))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:limit]
        return [self._bm25_payloads[i] for i in ranked]

    def _rrf_fuse(self, dense: list[dict], lexical: list[dict], top_k: int) -> list[dict]:
        """README §7C — RRF: score(doc) = Σ 1 / (60 + rank)."""
        fused: dict[tuple, float] = {}
        payload_by_key: dict[tuple, dict] = {}

        def _key(p: dict) -> tuple:
            return (p.get("source"), p.get("chunk_index"))

        for lane in (dense, lexical):
            for rank, payload in enumerate(lane):
                k = _key(payload)
                fused[k] = fused.get(k, 0.0) + 1.0 / (RRF_K + rank)
                payload_by_key[k] = payload

        ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
        return [payload_by_key[k] for k, _ in ordered]

    def retrieve(self, question: str) -> list[dict]:
        dense = self._dense_search(question, DENSE_TOP_K)
        lexical = self._bm25_search(question, BM25_TOP_K)
        return self._rrf_fuse(dense, lexical, RRF_FUSE_TOP_K)

    # ---- README §7E — grounded answer ----
    def ask(self, question: str, top_k: int = ANSWER_TOP_K) -> tuple[str, list[dict]]:
        hits = self.retrieve(question)[:top_k]
        if not hits:
            return REFUSAL_STRING, []

        blocks: list[str] = []
        sources: list[dict] = []
        for i, h in enumerate(hits, start=1):
            src = h.get("source", "") or ""
            section = h.get("section", "") or ""
            body = h.get("text", "") or ""
            sources.append(
                {
                    "index": i,
                    "source": src,
                    "section": section,
                    "char_start": h.get("char_start"),
                    "char_end": h.get("char_end"),
                    "lang": h.get("lang"),
                    "text": body[:1200] + ("…" if len(body) > 1200 else ""),
                }
            )
            tag = f"[{i}] {src}" + (f" · {section}" if section else "")
            blocks.append(f"{tag}\n{body}")
        context = "\n\n---\n\n".join(blocks)

        system = (
            "You are Krishi-Sakhi, an assistant for India's rural livelihood schemes. "
            "Answer using ONLY the provided context. "
            "Attach a bracketed source tag like [1] after every factual sentence. "
            "Answer in the SAME language the question was asked in. "
            f'If the context does not contain the answer, reply exactly: "{REFUSAL_STRING}"'
        )
        user_msg = f"Context:\n{context}\n\nQuestion: {question}"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ]

        try:
            completion = self._chat_openai.chat.completions.create(
                model=self._cfg.chat_model, messages=messages, temperature=CHAT_TEMPERATURE,
            )
        except Exception as e_zero:
            print(f"temperature={CHAT_TEMPERATURE} rejected ({e_zero}); retrying at {CHAT_TEMPERATURE_FALLBACK}.")
            try:
                completion = self._chat_openai.chat.completions.create(
                    model=self._cfg.chat_model, messages=messages, temperature=CHAT_TEMPERATURE_FALLBACK,
                )
            except Exception as e_fb:
                raise RuntimeError(f"MaaS chat call failed at both temperatures: {e_fb}") from e_fb

        answer = (completion.choices[0].message.content or "").strip()
        return answer, sources
