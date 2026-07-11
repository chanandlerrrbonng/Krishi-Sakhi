"""
Krishi-Sakhi — shared RAG logic for the Streamlit chat UI and deployment.
Mirrors qna.ipynb. README.md is the single source of truth.

README §6  — hard constraints (client-side hybrid, manual query prefix, no query_points)
README §7B/§7C/§7D/§7E — embeddings, hybrid retrieval, citations, grounded prompt
README S1  — cross-encoder reranker  |  README S3 — calibrated abstention
README S5  — PII redaction + jailbreak/injection filter (query- and display-time)
"""

from __future__ import annotations

import math
import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi

_REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_REPO_ROOT / ".env", override=True)

# ---- Reranker cache hygiene ----
# README §6 Correction 3 / S1: the reranker is meant to be baked into the
# deploy image at build time, never downloaded on first request. In local
# dev there's no image build step, so the first launch after adding this
# feature *will* pull ~2.3GB from HF Hub once. Pointing the cache somewhere
# persistent under the repo (rather than the ephemeral container home dir
# some notebook/JupyterHub environments wipe on restart) means it only
# ever happens once. Never Ctrl-C mid-download — that interrupted download
# thread pool colliding with Streamlit's script-rerun is exactly what
# produced the "Event loop is closed" crash. Let it finish once.
os.environ.setdefault("HF_HOME", str(_REPO_ROOT / ".hf_cache"))

# ---- README §6 Corr. 2 / §7B — Qwen3 query-instruction prefix (query path only, English) ----
QWEN_INSTRUCT = "Instruct: Given a question, retrieve passages that answer it\nQuery:"

# ---- README §7C — hybrid retrieval constants ----
DENSE_TOP_K = 20
BM25_TOP_K = 20
RRF_FUSE_TOP_K = 12
RRF_K = 60
ANSWER_TOP_K = 4  # README S1 pipeline tail — reranker feeds this.

# ---- README S1 — reranker config ----
# Set RERANKER_MODEL=none (or SKIP_RERANKER=true) to skip the local
# bge-reranker-v2-m3 download entirely — useful in ephemeral dev containers
# where the HF cache doesn't survive a restart, while you confirm whether
# Vayu MaaS exposes a hosted reranker per README §6 Correction 3. With it
# skipped, retrieval still works (dense+BM25 RRF fusion order), just without
# reranking or the calibrated-abstention confidence gate (S3).
_RERANKER_RAW = os.environ.get("RERANKER_MODEL", "").strip()
_SKIP_RERANKER = _RERANKER_RAW.lower() == "none" or os.environ.get("SKIP_RERANKER", "").strip().lower() in ("1", "true", "yes")
RERANKER_MODEL = "" if _SKIP_RERANKER else (_RERANKER_RAW or "BAAI/bge-reranker-v2-m3")
# README S1 explicitly says "keep the fused top-12 to hand to the reranker."
# This had been dropped to 8 for CPU speed, which silently drops the correct
# passage for paraphrased queries whose BM25 term-overlap is weaker — causing
# inconsistent abstention on semantically identical questions. Reverted to spec.
RERANK_INPUT_TOP_K = 12

# ---- README S3 — calibrated abstention (mean of top-N sigmoid scores) ----
# bge-reranker-v2-m3 relevant-passage sigmoids commonly sit ~0.3–0.6, NOT ~0.9.
# 0.62 was the README's illustrative placeholder and is far too high in practice.
ABSTAIN_THRESHOLD = float(os.environ.get("ABSTAIN_THRESHOLD", "").strip() or "0.28")
ABSTAIN_SCORE_TOPN = 3   # average the top-3 reranker scores for a stable gate

# ---- README §7E — grounded-answer prompt config ----
CHAT_TEMPERATURE = 0.0
CHAT_TEMPERATURE_FALLBACK = 0.1
REFUSAL_STRING = "I could not find this in the provided documents."

# ---- README S5 — PII redaction (Aadhaar / PAN / phone), script-agnostic regex ----
# Scoped per README: Presidio's default models are English-only, so a full Hindi PII
# NER pipeline is out of scope. These Indian ID formats are Latin/numeric, so plain
# regex covers the highest-value cases honestly, regardless of query language.
# Order matters: Aadhaar (12 digits) is matched and masked BEFORE the phone pattern
# (10 digits) runs, so a redacted Aadhaar number can't leave a residual digit run
# that the phone pattern then partially matches.
_PII_PATTERNS: list[tuple[str, "re.Pattern[str]"]] = [
    ("AADHAAR", re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")),
    ("PAN", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")),
    ("PHONE", re.compile(r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b")),
]


def redact_pii(text: str) -> str:
    """README S5 — mask Aadhaar / PAN / phone-number patterns. Applied to the user's
    question, the retrieved context handed to the LLM, and the sources shown in the UI —
    i.e. both at query time and at display time, per README §8 S5."""
    if not text:
        return text
    redacted = text
    for label, pattern in _PII_PATTERNS:
        redacted = pattern.sub(f"[REDACTED-{label}]", redacted)
    return redacted


# ---- README S5 — jailbreak / prompt-injection filter ----
# Curated keyword/regex filter, run BEFORE retrieval, blocking on a positive hit —
# matches the README's scoped approach (a cheap classifier, not a full moderation model).
JAILBREAK_BLOCK_STRING = (
    "This request can't be processed. Please ask a question about the ingested "
    "scheme guidelines (PM-KISAN, PM-KMY, Namo Drone Didi, SHG · DAY-NRLM, KCC, "
    "RBI Circular, PMFBY)."
)
_JAILBREAK_PATTERNS = [
    re.compile(r"ignore (all|any|previous|prior|the) (instructions?|prompts?|rules?)", re.I),
    re.compile(r"disregard (all|any|previous|prior|the) (instructions?|prompts?|rules?)", re.I),
    re.compile(r"\byou are (now|no longer)\b", re.I),
    re.compile(r"reveal (your|the) (system prompt|instructions|guidelines)", re.I),
    re.compile(r"\bpretend (you are|to be)\b", re.I),
    re.compile(r"\bact as (if )?(you|a)\b", re.I),
    re.compile(r"\bDAN\b"),
    re.compile(r"jailbreak", re.I),
    re.compile(r"override (your|the) (guidelines|instructions|rules|safety)", re.I),
    re.compile(r"system prompt", re.I),
]


def is_jailbreak_attempt(text: str) -> bool:
    return any(p.search(text) for p in _JAILBREAK_PATTERNS)


# ---- Streaming language-correction sentinel ----
# README S4's corrective retry (§ "Belt-and-suspenders" below) previously only ran on
# the non-streaming ask() path — chat_app.py always streams, so it was dead code in
# production. The streaming generator now yields this marker + the corrected full
# answer as its final chunk when a language-mismatch retry succeeds; chat_app.py
# detects the prefix and replaces its running buffer wholesale instead of appending.
LANG_CORRECTION_MARKER = "\x00__KRISHI_SAKHI_LANG_CORRECTED__\x00"

_PLACEHOLDER_MARKERS = ("<VAYU_", "<YOUR_", "<COLLECTION", "<", "***")


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise EnvironmentError(
            f"Missing required environment variable {name!r}. "
            f"Set it in ask-it/.env (copy from .env.example)."
        )
    if any(marker in value for marker in _PLACEHOLDER_MARKERS):
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


def detect_script_lang(text: str) -> str:
    """Cheap, deterministic Devanagari detection — shared with the UI (no langdetect noise)."""
    for ch in text:
        if "\u0900" <= ch <= "\u097F":
            return "hi"
    return "en"


def answer_language_directive(question: str) -> tuple[str, str]:
    """Return (lang_code, explicit directive) forcing the answer language.
    Overrides context-language drift, which soft instructions cannot."""
    lang = detect_script_lang(question)
    if lang == "hi":
        directive = (
            "The user's question is in Hindi. You MUST write your ENTIRE answer in Hindi "
            "(Devanagari script). Do not answer in English."
        )
    else:
        directive = (
            "The user's question is in English. You MUST write your ENTIRE answer in English. "
            "Do not answer in Hindi or any other language, even if the source passages are in Hindi."
        )
    return lang, directive


def _sigmoid(x: float) -> float:
    # numerically stable
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    z = math.exp(x)
    return z / (1.0 + z)


@dataclass
class RAGConfig:
    collection_name: str
    embedding_model: str
    chat_model: str
    embed_batch_size: int


def load_config() -> RAGConfig:
    return RAGConfig(
        collection_name=os.environ.get("COLLECTION_NAME", "").strip() or "krishi_sakhi_rag",
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
    """Query-time RAG: hybrid retrieve → cross-encoder rerank → abstain-or-answer, cited."""

    def __init__(self) -> None:
        self._cfg = load_config()
        self._qdrant = build_qdrant_client()
        self._embedding_openai = build_openai_client(is_embedding=True)
        self._chat_openai = build_openai_client(is_embedding=False)
        # README §7C — build BM25 ONCE at engine init (never rebuilt live).
        self._bm25: BM25Okapi | None = None
        self._bm25_payloads: list[dict] = []
        self._build_bm25_index()
        # README S1 — reranker baked into the container / loaded once.
        self._reranker = self._load_reranker()

    @property
    def config(self) -> RAGConfig:
        return self._cfg

    @property
    def abstain_threshold(self) -> float:
        """README S3 — the actual calibrated gate the UI should display, not a
        hardcoded copy that can drift from the runtime value."""
        return ABSTAIN_THRESHOLD

    @property
    def has_reranker(self) -> bool:
        """README S1/S3 — whether the calibrated-abstention gate is actually live.
        False when RERANKER_MODEL=none / SKIP_RERANKER=true — the UI should not
        claim the confidence gate is active when it isn't."""
        return self._reranker is not None

    # ---- README S1 — cross-encoder reranker (local; MaaS-first is a deploy-time swap) ----
    def _load_reranker(self):
        if not RERANKER_MODEL:
            print(
                "NOTE: local reranker skipped (RERANKER_MODEL=none / SKIP_RERANKER=true). "
                "Retrieval runs on dense+BM25 RRF fusion only — no reranking, no S3 "
                "calibrated-abstention gate. Unset this once you've confirmed whether "
                "Vayu MaaS has a hosted reranker, or you're ready for the local one-time download."
            )
            return None
        try:
            from sentence_transformers import CrossEncoder
        except Exception as e:  # pragma: no cover
            print(f"WARNING: sentence-transformers unavailable ({e}); reranking disabled.")
            return None
        try:
            from huggingface_hub import scan_cache_dir
            cached = any(repo.repo_id == RERANKER_MODEL for repo in scan_cache_dir().repos)
        except Exception:
            cached = False
        if not cached:
            print(
                f"NOTE: {RERANKER_MODEL!r} is not cached locally — this will download "
                "~2.3GB from HF Hub now (one-time, per README §6 Correction 3). "
                "Let it finish; interrupting it mid-download is what previously crashed "
                "the app. This only happens once. To skip this, set RERANKER_MODEL=none."
            )
        try:
            # max_length cap keeps CPU inference fast; long chunks are truncated for scoring only.
            return CrossEncoder(RERANKER_MODEL, max_length=512)
        except Exception as e:  # pragma: no cover
            print(f"WARNING: could not load reranker {RERANKER_MODEL!r} ({e}); reranking disabled.")
            return None

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
            # Fail loud and hard — a silent dense-only fallback masks an un-ingested collection.
            self._bm25 = None
            raise RuntimeError(
                f"Collection {self._cfg.collection_name!r} is EMPTY. "
                "Run the ingest notebook (qna.ipynb) before launching the app."
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

    # ---- README S1 — rerank + README S3 — stable gate score (mean of top-N sigmoids) ----
    def _rerank(self, question: str, candidates: list[dict]) -> tuple[list[dict], float]:
        if not candidates:
            return [], 0.0
        if self._reranker is None:
            # Reranker unavailable: keep RRF order, no calibrated score available.
            return candidates, 1.0
        subset = candidates[:RERANK_INPUT_TOP_K]
        pairs = [(question, c.get("text", "") or "") for c in subset]
        logits = self._reranker.predict(pairs)
        scored = sorted(zip(subset, logits), key=lambda t: float(t[1]), reverse=True)
        ordered = [c for c, _ in scored]
        # Any candidates beyond the reranked subset keep their RRF order behind the reranked ones.
        ordered += candidates[RERANK_INPUT_TOP_K:]
        top_sigmoids = [_sigmoid(float(s)) for _, s in scored[:ABSTAIN_SCORE_TOPN]]
        gate_score = sum(top_sigmoids) / len(top_sigmoids)
        return ordered, gate_score

    # ---- README §7E + S1 + S3 + S5 — grounded answer, guarded, with calibrated abstention ----
    def ask(self, question: str, top_k: int = ANSWER_TOP_K, stream: bool = False):
        """Returns (answer, sources, gate_score) when stream=False,
        or (token_generator, meta_callback) when stream=True, where
        meta_callback() -> {"sources": [...], "gate_score": float}.

        gate_score is the calibrated confidence (README S3) — None when no
        reranker is loaded, so the UI can distinguish "low confidence" from
        "confidence not computed" instead of showing a fake number.
        """
        # README S5 — PII redaction on the query itself, before it touches embedding
        # or chat APIs at all (not just at display time).
        question = redact_pii(question)

        # README S5 — jailbreak/injection filter, run BEFORE retrieval, blocks on a hit.
        if is_jailbreak_attempt(question):
            if not stream:
                return JAILBREAK_BLOCK_STRING, [], None
            return iter([JAILBREAK_BLOCK_STRING]), (lambda: {"sources": [], "gate_score": None})

        fused = self.retrieve(question)
        if not fused:
            if not stream:
                return REFUSAL_STRING, [], None
            return iter([REFUSAL_STRING]), (lambda: {"sources": [], "gate_score": None})

        ranked, gate_score = self._rerank(question, fused)
        # None-able gate score for display: the reranker returns a sentinel 1.0 when
        # it isn't loaded (see _rerank) — that isn't a real calibrated score, so don't
        # surface it as one.
        display_gate_score = gate_score if self._reranker is not None else None

        # README S3 — abstain only when confidence is CLEARLY low (stable mean-of-top-N gate).
        if self._reranker is not None and gate_score < ABSTAIN_THRESHOLD:
            if not stream:
                return REFUSAL_STRING, [], display_gate_score
            return iter([REFUSAL_STRING]), (lambda: {"sources": [], "gate_score": display_gate_score})

        hits = ranked[:top_k]
        blocks: list[str] = []
        sources: list[dict] = []
        for i, h in enumerate(hits, start=1):
            src = h.get("source", "") or ""
            section = h.get("section", "") or ""
            # README S5 — redact PII from retrieved context before it reaches the LLM
            # prompt or the UI's source panel (display-time redaction).
            body = redact_pii(h.get("text", "") or "")
            lang = h.get("lang") or detect_script_lang(body)
            sources.append(
                {
                    "index": i,
                    "source": src,
                    "section": section,
                    "page": h.get("page"),
                    "char_start": h.get("char_start"),
                    "char_end": h.get("char_end"),
                    "lang": lang,
                    "text": body[:1200] + ("…" if len(body) > 1200 else ""),
                }
            )
            tag = f"[{i}] {src}" + (f" · {section}" if section else "")
            blocks.append(f"{tag}\n{body}")
        context = "\n\n---\n\n".join(blocks)

        lang, lang_directive = answer_language_directive(question)

        system = (
            "You are Krishi-Sakhi, an assistant for India's rural livelihood schemes. "
            "Answer using ONLY the provided context. "
            "Attach a bracketed source tag like [1] after every factual sentence. "
            "Use ONLY [1]-style numeric citations that match the context blocks — "
            "never invent citation markers. "
            f"{lang_directive} "
            f'If the context does not contain the answer, reply exactly: "{REFUSAL_STRING}"'
        )
        # The directive is repeated here, right next to the question, because a
        # single system-prompt mention gets out-competed by a large Hindi-heavy
        # context block sitting above it in the prompt — models weight
        # instructions near the end of the turn more heavily than ones buried
        # under several KB of source text. This is what was causing English
        # questions to come back answered in Hindi despite the system prompt
        # already saying not to.
        user_msg = (
            f"Context:\n{context}\n\nQuestion: {question}\n\n"
            f"(Reminder: {lang_directive})"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ]

        def _corrective_retry(current_answer: str) -> str | None:
            """README S4 belt-and-suspenders — shared by both the streaming and
            non-streaming paths (previously only reachable from non-streaming)."""
            retry_messages = messages + [
                {"role": "assistant", "content": current_answer},
                {
                    "role": "user",
                    "content": (
                        "That reply was in the wrong language. Rewrite the ENTIRE answer in "
                        + ("Hindi (Devanagari script)." if lang == "hi" else "English.")
                        + " Keep the same citations and content, just change the language."
                    ),
                },
            ]
            try:
                retry = self._chat_openai.chat.completions.create(
                    model=self._cfg.chat_model, messages=retry_messages, temperature=CHAT_TEMPERATURE,
                )
                retry_answer = (retry.choices[0].message.content or "").strip()
                if retry_answer and retry_answer != REFUSAL_STRING:
                    return redact_pii(retry_answer)
            except Exception:
                pass  # keep the original answer rather than fail the whole request
            return None

        if stream:
            def _gen():
                parts: list[str] = []
                try:
                    resp = self._chat_openai.chat.completions.create(
                        model=self._cfg.chat_model, messages=messages,
                        temperature=CHAT_TEMPERATURE, stream=True,
                    )
                except Exception:
                    resp = self._chat_openai.chat.completions.create(
                        model=self._cfg.chat_model, messages=messages,
                        temperature=CHAT_TEMPERATURE_FALLBACK, stream=True,
                    )
                for chunk in resp:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        parts.append(delta)
                        yield delta

                full_answer = "".join(parts).strip()
                if full_answer == REFUSAL_STRING:
                    return  # model self-refused correctly; nothing to correct

                # README S4 — this check previously only existed on the non-streaming
                # path, which chat_app.py never calls. Now it actually runs.
                if detect_script_lang(full_answer) != lang:
                    corrected = _corrective_retry(full_answer)
                    if corrected:
                        # Signal the UI to discard the wrong-language draft and swap
                        # in the corrected full answer, instead of appending to it.
                        yield LANG_CORRECTION_MARKER + corrected

            return _gen(), (lambda: {"sources": sources, "gate_score": display_gate_score})

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
        # If the model emitted the refusal string, present it as an abstention with no sources.
        if answer == REFUSAL_STRING:
            return REFUSAL_STRING, [], display_gate_score

        # Belt-and-suspenders: even with the reminder above, the answer language
        # can still drift to match the (often Hindi-heavy) source docs rather
        # than the question. One corrective retry before we give up and return
        # what we have.
        if detect_script_lang(answer) != lang:
            corrected = _corrective_retry(answer)
            if corrected:
                answer = corrected

        return redact_pii(answer), sources, display_gate_score