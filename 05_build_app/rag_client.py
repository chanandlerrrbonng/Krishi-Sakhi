"""
Krishi-Sakhi — shared RAG logic for the Streamlit chat UI and deployment.
Mirrors qna.ipynb. README.md is the single source of truth.

README §6  — hard constraints (client-side hybrid, manual query prefix, no query_points)
README §7B/§7C/§7D/§7E — embeddings, hybrid retrieval, citations, grounded prompt
README S1  — cross-encoder reranker  |  README S3 — calibrated abstention
README S5  — PII redaction + jailbreak/injection filter (query- and display-time)

PERF NOTE (this pass): every change below is mechanical — concurrency, hardware
utilization, avoiding a wasted network round-trip on a request that will only
ever fail. Nothing here changes retrieval order, RRF scoring, the abstention
threshold, prompt content, or citation logic. Search "PERF:" to find each spot.

LATENCY PASS 2 (this edit): further latency work, again WITHOUT changing what
gets retrieved, in what order, the gate value, the prompt, or citations. All of
it is either (a) guaranteed-identical-output caching/threading, or (b) OFF by
default and gated behind an env flag you must opt into (reranker backend /
precision), because those *could* perturb scores by a hair and the brief is
"don't touch accuracy at all". Search "LAT2:" to find each spot. Concretely:
  LAT2-1  query-embedding LRU cache (identical text -> identical vector; the
          FAQ buttons and repeated questions now skip the embed round-trip).
  LAT2-2  torch.inference_mode() + no_grad around reranker scoring (no autograd
          bookkeeping; identical numbers, less overhead).
  LAT2-3  opt-in reranker backend (onnx / openvino) + opt-in fp16/bf16, both
          default OFF so stock behavior is byte-identical to before.
  LAT2-4  reranker candidate cap is now env-tunable (RERANK_INPUT_TOP_K) but
          DEFAULTS to the same value as before, so default output is identical;
          lower it yourself only if you accept the (tiny) reorder risk.
  LAT2-5  reuse a single embedding-input list allocation / minor hot-path tidy.
"""

from __future__ import annotations

import math
import os
import re
from functools import lru_cache
from pathlib import Path
from dataclasses import dataclass
from typing import Any
from concurrent.futures import ThreadPoolExecutor  # PERF: parallel dense+BM25

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
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
# Wider retrieval because corpus is small and false abstentions are worse
# than reranking a few extra chunks.
DENSE_TOP_K = int(os.environ.get("DENSE_TOP_K", "80"))
BM25_TOP_K = int(os.environ.get("BM25_TOP_K", "80"))
RRF_FUSE_TOP_K = int(os.environ.get("RRF_FUSE_TOP_K", "80"))

RRF_K = 60
DENSE_RRF_WEIGHT = 1.0
BM25_RRF_WEIGHT = 0.5
# Prevent BM25 from injecting arbitrary zero-score chunks into RRF.
BM25_MIN_SCORE = 1e-9
# If a scheme is detected, append/rerank many chunks from that scheme.
EXHAUSTIVE_SCHEME_TOP_K = int(os.environ.get("SCHEME_EXHAUSTIVE_TOP_K", "60"))
# If the total corpus is very small, allow exhaustive fallback.
SMALL_CORPUS_EXHAUSTIVE_MAX = int(os.environ.get("SMALL_CORPUS_EXHAUSTIVE_MAX", "80"))

ANSWER_TOP_K = int(os.environ.get("ANSWER_TOP_K", "5"))

# CHAIN: how many prior USER turns to fold into the retrieval query for
# referential follow-ups. Kept small on purpose — just enough to resolve
# "it"/"that scheme" against the immediately preceding question(s). This
# NEVER affects what the LLM is asked to answer, only what we search with.
HISTORY_QUERY_TURNS = 2

# CONTEXT: hard character cap per context block handed to the LLM. Mirrors the
# existing [:1200] UI-sources truncation so a single long chunk can't blow up
# the prompt. Purely a budget guard — does not change which chunks are chosen
# or their order.
CONTEXT_CHAR_BUDGET = 1500

# LAT2-1: query-embedding cache size. Identical query text always produces an
# identical vector from the embedding model, so caching is byte-for-byte safe
# and simply removes the network round-trip for repeated/identical queries
# (the FAQ buttons send the exact same string every time; follow-up-expanded
# retrieval queries also repeat). 0 disables it. This is a pure latency win
# with zero effect on retrieval/scoring.
QUERY_EMBED_CACHE_SIZE = int(os.environ.get("QUERY_EMBED_CACHE_SIZE", "256"))

# ---- RETRIEVAL FIX: explicit scheme/source constraint for named-scheme queries ----
# If the user explicitly names a scheme, retrieval must not let another loan/credit
# document crowd it out merely because it shares generic finance terms.

_SCHEME_CANONICAL_NAME: dict[str, str] = {
    "AIF": "Agriculture Infrastructure Fund",
    "KCC": "Kisan Credit Card",
    "PMFBY": "Pradhan Mantri Fasal Bima Yojana",
    "PM_KISAN": "PM-KISAN",
    "PM_KMY": "PM-KMY",
    "NAMO_DRONE_DIDI": "Namo Drone Didi",
    "DAY_NRLM_SHG": "DAY-NRLM Self Help Group",
    "RBI": "Reserve Bank of India",
    "PM_KUSUM": "PM-KUSUM",
    "PMFME": "PMFME",
    "FPO": "FPO scheme",
}

_SCHEME_ALIASES: dict[str, tuple[str, ...]] = {
    "AIF": (
        "aif",
        "agriculture infrastructure fund",
        "agri infrastructure fund",
        "agri infra fund",
        "कृषि अवसंरचना निधि",
        "कृषि अवसंरचना कोष",
    ),
    "KCC": (
        "kcc",
        "kisan credit card",
        "किसान क्रेडिट कार्ड",
    ),
    "PMFBY": (
        "pmfby",
        "fasal bima",
        "pradhan mantri fasal bima yojana",
        "प्रधानमंत्री फसल बीमा योजना",
        "फसल बीमा",
    ),
    "PM_KISAN": (
        "pm-kisan",
        "pm kisan",
        "pradhan mantri kisan samman nidhi",
        "प्रधानमंत्री किसान सम्मान निधि",
        "पीएम किसान",
    ),
    "PM_KMY": (
        "pm-kmy",
        "pm kmy",
        "kisan maan dhan",
        "kisan mandhan",
        "maan dhan",
        "किसान मान धन",
    ),
    "NAMO_DRONE_DIDI": (
        "namo drone didi",
        "drone didi",
        "नमो ड्रोन दीदी",
        "ड्रोन दीदी",
    ),
    "DAY_NRLM_SHG": (
        "day-nrlm",
        "day nrlm",
        "nrlm",
        "shg",
        "self help group",
        "स्वयं सहायता समूह",
        "एसएचजी",
        "एनआरएलएम",
    ),
    "RBI": (
        "rbi",
        "reserve bank of india",
        "reserve bank",
        "भारतीय रिजर्व बैंक",
        "आरबीआई",
    ),
    "PM_KUSUM": (
        "pm-kusum",
        "pm kusum",
        "kusum",
        "कुसुम",
    ),
    "PMFME": (
        "pmfme",
        "pm fme",
        "micro food processing",
        "सूक्ष्म खाद्य प्रसंस्करण",
    ),
    "FPO": (
        "fpo",
        "farmer producer organisation",
        "farmer producer organization",
        "किसान उत्पादक संगठन",
    ),
}

_SCHEME_INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "NAMO_DRONE_DIDI": (
        "drone",
        "spraying drone",
        "agricultural drone",
        "custom hiring centre",
        "custom hiring center",
        "कस्टम हायरिंग",
        "ड्रोन",
    ),
    "PM_KUSUM": (
        "solar pump",
        "solar pumps",
        "solarisation",
        "solarization",
        "कुसुम",
        "सोलर पंप",
    ),
    "PMFBY": (
        "crop insurance",
        "fasal insurance",
        "insurance premium",
        "claim amount",
        "insured crop",
        "फसल बीमा",
        "बीमा प्रीमियम",
        "दावा राशि",
    ),
    "PM_KMY": (
        "monthly pension",
        "pension",
        "entry age",
        "18 to 40",
        "60 years",
        "मान धन",
        "पेंशन",
    ),
    "PM_KISAN": (
        "income support",
        "annual support",
        "installment",
        "instalment",
        "landholding farmer",
        "किसान सम्मान निधि",
        "किस्त",
    ),
    "KCC": (
        "kisan credit",
        "crop loan",
        "interest subvention",
        "working capital loan",
        "किसान क्रेडिट",
        "ब्याज सब्वेंशन",
    ),
    "AIF": (
        "agriculture infrastructure",
        "agri infrastructure",
        "post harvest",
        "infrastructure fund",
        "credit guarantee",
        "कृषि अवसंरचना",
    ),
    "DAY_NRLM_SHG": (
        "self help group",
        "shg loan",
        "collateral free",
        "bank linkage",
        "स्वयं सहायता समूह",
        "बिना गारंटी",
    ),
    "PMFME": (
        "food processing",
        "micro food processing",
        "micro enterprise",
        "odop",
        "seed capital",
        "खाद्य प्रसंस्करण",
    ),
    "FPO": (
        "farmer producer organisation",
        "farmer producer organization",
        "producer organization",
        "producer organisation",
        "equity grant",
        "cbbo",
        "किसान उत्पादक संगठन",
    ),
}

_SCHEME_SOURCE_HINTS: dict[str, tuple[str, ...]] = {
    "AIF": ("aif", "agriculture infrastructure"),
    "KCC": ("kcc", "kisan credit card"),
    "PMFBY": ("pmfby", "fasal bima"),
    "PM_KISAN": ("pm-kisan", "pm_kisan", "pmkisan", "kisan samman"),
    "PM_KMY": ("pmkmy", "pm-kmy", "maan dhan", "mandhan"),
    "NAMO_DRONE_DIDI": ("drone didi", "namo drone"),
    "DAY_NRLM_SHG": ("nrlm", "shg", "self help"),
    "RBI": ("rbi", "reserve bank"),
    "PM_KUSUM": ("kusum",),
    "PMFME": ("pmfme",),
    "FPO": ("fpo",),
}


def _scheme_norm(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[-–—_/]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _contains_alias(norm_text: str, alias: str) -> bool:
    alias_norm = _scheme_norm(alias)
    if not alias_norm:
        return False
    return re.search(rf"(?<!\w){re.escape(alias_norm)}(?!\w)", norm_text, re.UNICODE) is not None


def _detect_explicit_schemes(text: str) -> set[str]:
    norm = _scheme_norm(text)
    out: set[str] = set()
    for scheme, aliases in _SCHEME_ALIASES.items():
        if any(_contains_alias(norm, alias) for alias in aliases):
            out.add(scheme)
    return out


def _detect_intent_schemes(text: str) -> set[str]:
    norm = _scheme_norm(text)
    out: set[str] = set()
    for scheme, keywords in _SCHEME_INTENT_KEYWORDS.items():
        if any(_contains_alias(norm, kw) for kw in keywords):
            out.add(scheme)
    return out


def _infer_schemes_from_source(source: str) -> set[str]:
    s = source.lower()
    out: set[str] = set()
    for scheme, hints in _SCHEME_SOURCE_HINTS.items():
        if any(hint in s for hint in hints):
            out.add(scheme)
    return out


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

# LAT2-3: OPT-IN reranker acceleration. All three default to the stock PyTorch
# fp32 path, so with no env set the reranker produces byte-identical scores to
# before — accuracy is untouched. Flip these only if you're willing to A/B a
# hair of numerical drift for a real CPU/GPU speedup:
#   RERANKER_BACKEND = onnx | openvino   (CPU: often 1.5-3x at batch<=16; needs
#                       `pip install sentence-transformers[onnx]` or [openvino];
#                       first run exports the model once, then cache it)
#   RERANKER_DTYPE   = float16 | bfloat16  (GPU only; "minimal" score change per
#                       the sentence-transformers docs, still off by default)
RERANKER_BACKEND = os.environ.get("RERANKER_BACKEND", "").strip().lower()  # "", "onnx", "openvino"
RERANKER_DTYPE = os.environ.get("RERANKER_DTYPE", "").strip().lower()      # "", "float16", "bfloat16"

# RECALL FIX: kept in lockstep with RRF_FUSE_TOP_K above (was 12/12, now
# 20/20) — this used to be a no-op slice since it equaled the fusion cutoff
# anyway. If you ever raise RRF_FUSE_TOP_K again, raise this to match, or the
# reranker will silently go back to only seeing a truncated subset of it.
#
# LAT2-4: now env-tunable. DEFAULT is unchanged (EXHAUSTIVE_SCHEME_TOP_K = 60),
# so default output is identical. The reranker is the single most expensive
# stage on CPU and its cost is ~linear in the number of (query, passage) pairs
# it scores. If — and ONLY if — you accept that a very low-RRF-ranked chunk
# could in principle rerank into the top-5/top-3-gate (in practice almost never,
# since RRF already front-loads the relevant chunks), you can set e.g.
# RERANK_INPUT_TOP_K=24 to roughly halve reranker latency. Left at 60 here so
# nothing changes unless you choose to.
RERANK_INPUT_TOP_K = int(
    os.environ.get("RERANK_INPUT_TOP_K", str(EXHAUSTIVE_SCHEME_TOP_K))
)

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
    i.e. both at query time and at display time, per README §8 S5.

    NOTE: this is intentionally NOT applied to document text at ingest time anymore.
    Redacting before embedding permanently deleted real answer content (e.g. a bare
    12-digit scheme figure the Aadhaar pattern false-matched), producing correct-looking
    abstentions with no way to debug. Redaction now happens ONLY at query/display time,
    which still satisfies S5 (nothing un-redacted ever reaches the LLM or the UI)."""
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
    # PERF/FIX: without an explicit timeout, a stalled MaaS call (embedding or
    # chat) can hang far longer than the default client allows, and the app
    # has no way to distinguish "slow" from "stuck". 30s is generous for a
    # single embedding/chat call; max_retries=1 avoids compounding a stall
    # with silent retries that double the wait.
    return OpenAI(api_key=api_key, base_url=base_url, timeout=30.0, max_retries=1)


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
        self._payload_key_to_index: dict[tuple, int] = {}
        self._sources_by_scheme: dict[str, set[str]] = {}
        self._build_bm25_index()
        # README S1 — reranker baked into the container / loaded once.
        self._reranker = self._load_reranker()

        # PERF: one shared executor, reused across every query, instead of
        # spinning up threads per-request. Used to run dense search (network-
        # bound: embed call + Qdrant round trip) concurrently with BM25
        # (local CPU) rather than paying both costs back-to-back.
        self._executor = ThreadPoolExecutor(max_workers=4)

        # PERF: some MaaS gateways reject temperature=0.0 outright. Previously
        # every single query re-attempted temp=0, ate a failed round trip,
        # then fell back to 0.1 — forever, on every request. Decide this once
        # (via a harmless warmup call below) and remember it, so steady-state
        # queries go straight to whichever temperature actually works.
        self._temp0_supported = True

        # OBSERVABILITY: how many times the language-correction retry has fired
        # this process. Cheap counter so you can tell whether the corrective
        # retry (which costs ~2x tokens when it runs) is a rare safety net or a
        # frequent tax. Read via corrective_retry_count.
        self._corrective_retry_count = 0

        # LAT2-1: build the query-embedding cache. lru_cache-wrapped bound method
        # closure — identical text returns the memoized vector and skips the
        # embedding round-trip entirely. Byte-identical vectors, so retrieval and
        # scoring are unaffected; it only removes duplicate network calls.
        self._embed_query_cached = self._make_query_embed_cache()

        # PERF: warm up the embedding client and reranker once here, inside
        # the already-cached engine init (@st.cache_resource in chat_app.py),
        # so any first-call lazy-init cost (connection setup, CUDA context,
        # thread-pool spin-up) happens at app startup rather than during a
        # user's first real question. Best-effort — never let warmup failures
        # block the app from starting.
        self._warmup()

    def _make_query_embed_cache(self):
        """LAT2-1: return a cached wrapper over the (prefixed) query embedding.
        Keyed on the raw question string; the QWEN_INSTRUCT prefix is applied
        inside, so the cache key stays human-readable and the embedded text is
        exactly what it was before."""
        if QUERY_EMBED_CACHE_SIZE <= 0:
            # Caching disabled — behave exactly like the old direct path.
            def _direct(question: str) -> tuple[float, ...]:
                return tuple(self.embed_texts([f"{QWEN_INSTRUCT}{question}"])[0])
            return _direct

        @lru_cache(maxsize=QUERY_EMBED_CACHE_SIZE)
        def _cached(question: str) -> tuple[float, ...]:
            # Store as a tuple so lru_cache can hold it immutably; callers copy
            # back to a list. Same vector the model would return every time.
            return tuple(self.embed_texts([f"{QWEN_INSTRUCT}{question}"])[0])

        return _cached

    def _warmup(self) -> None:
        try:
            self.embed_texts(["warmup"])
        except Exception:
            pass
        if self._reranker is not None:
            try:
                self._reranker.predict([("warmup query", "warmup passage")],
                                        batch_size=1, show_progress_bar=False)
            except Exception:
                pass
        # Cheap, cache-safe probe of which temperature the chat endpoint accepts,
        # so the very first real user query doesn't pay for this discovery.
        try:
            self._chat_openai.chat.completions.create(
                model=self._cfg.chat_model,
                messages=[{"role": "user", "content": "hi"}],
                temperature=CHAT_TEMPERATURE,
                max_tokens=1,
            )
        except Exception:
            self._temp0_supported = False

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

    @property
    def corrective_retry_count(self) -> int:
        """OBSERVABILITY — number of language-correction retries fired this process."""
        return self._corrective_retry_count

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
        # PERF: use GPU automatically if one is present on this pod (same weights,
        # same precision, same scores — just faster). On CPU-only environments,
        # explicitly claim all available cores; some containers default torch to
        # 1-2 threads, which quietly starves cross-encoder inference.
        try:
            import torch
            if torch.cuda.is_available():
                device = "cuda"
            else:
                device = "cpu"
                torch.set_num_threads(os.cpu_count() or 4)
        except Exception:
            device = "cpu"

        # LAT2-3: assemble kwargs for optional backend / dtype acceleration.
        # With no env set these stay empty, so CrossEncoder is constructed
        # exactly as before (stock PyTorch fp32) → identical scores.
        ce_kwargs: dict[str, Any] = {"max_length": 512, "device": device}
        model_kwargs: dict[str, Any] = {}
        if RERANKER_DTYPE in ("float16", "bfloat16"):
            # GPU-only per the sentence-transformers docs; harmless string that
            # the library maps to torch dtype. Off by default.
            model_kwargs["torch_dtype"] = RERANKER_DTYPE
        if model_kwargs:
            ce_kwargs["model_kwargs"] = model_kwargs
        if RERANKER_BACKEND in ("onnx", "openvino"):
            # First run exports + (ideally) you save_pretrained() to cache it.
            # Requires the matching extra installed; if it fails we fall back
            # to the stock construction below so the app still boots.
            ce_kwargs["backend"] = RERANKER_BACKEND

        try:
            # max_length cap keeps CPU inference fast; long chunks are truncated for scoring only.
            from sentence_transformers import CrossEncoder as _CE
            return _CE(RERANKER_MODEL, **ce_kwargs)
        except Exception as e:  # pragma: no cover
            # If an opt-in accelerator (backend/dtype) failed to construct, retry
            # once with the plain, always-available fp32 PyTorch path so a bad
            # env flag degrades to "same as before" rather than "no reranker".
            if "backend" in ce_kwargs or "model_kwargs" in ce_kwargs:
                print(
                    f"WARNING: reranker accelerator ({RERANKER_BACKEND or RERANKER_DTYPE}) "
                    f"failed to load ({e}); falling back to stock fp32 PyTorch."
                )
                try:
                    from sentence_transformers import CrossEncoder as _CE2
                    return _CE2(RERANKER_MODEL, max_length=512, device=device)
                except Exception as e2:  # pragma: no cover
                    print(f"WARNING: could not load reranker {RERANKER_MODEL!r} ({e2}); reranking disabled.")
                    return None
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
        """Query path only — manual English instruction prefix (no prompt_name to MaaS).

        LAT2-1: routed through the LRU cache. The embedded text (prefix+question)
        is unchanged, so the returned vector is byte-identical to before; the
        cache only saves the round-trip when the same question text recurs
        (FAQ buttons, repeated/expanded retrieval queries)."""
        return list(self._embed_query_cached(question))

    # ---- README §7C — client-side BM25 ----
    # BM25 tokenizer: lowercase + unicode word extraction. The old `text.split()`
    # left punctuation attached ("PM-KISAN," != "pm-kisan") and was case-sensitive,
    # which starved the lexical lane exactly on keyword/paraphrased queries where
    # BM25 is meant to rescue dense-embedding drift — a direct cause of spurious
    # low-confidence abstentions. \w+ keeps Devanagari (unicode word chars) too.
    _TOKEN_RE = re.compile(r"\w+", re.UNICODE)

    @classmethod
    def _bm25_tokenize(cls, text: str) -> list[str]:
        return cls._TOKEN_RE.findall(text.lower())

    @staticmethod
    def _payload_key(payload: dict) -> tuple:
        return (payload.get("source"), payload.get("chunk_index"))

    @staticmethod
    def _payload_search_text(payload: dict) -> str:
        """Search/rerank text.

        New ingests store search_text directly. Older ingests still work because
        we synthesize the same header from metadata.
        """
        existing = payload.get("search_text")
        if isinstance(existing, str) and existing.strip():
            return existing

        scheme = payload.get("scheme")
        scheme_title = ""
        if isinstance(scheme, str) and scheme:
            scheme_title = _SCHEME_CANONICAL_NAME.get(scheme, scheme)

        parts: list[str] = []
        if scheme_title:
            parts.append(f"Scheme: {scheme_title}")
        if payload.get("source"):
            parts.append(f"Source file: {payload.get('source')}")
        if payload.get("section"):
            parts.append(f"Section: {payload.get('section')}")
        parts.append(payload.get("text", "") or "")

        return "\n".join(p for p in parts if p)

    @staticmethod
    def _schemes_for_payload(payload: dict) -> set[str]:
        schemes: set[str] = set()

        raw = payload.get("scheme")
        if isinstance(raw, str) and raw.strip():
            val = raw.strip()
            if val in _SCHEME_CANONICAL_NAME:
                schemes.add(val)
        elif isinstance(raw, (list, tuple, set)):
            for item in raw:
                if isinstance(item, str) and item.strip() in _SCHEME_CANONICAL_NAME:
                    schemes.add(item.strip())

        schemes |= _infer_schemes_from_source(payload.get("source", "") or "")
        return schemes

    def _payload_matches_schemes(self, payload: dict, schemes: set[str] | None) -> bool:
        if not schemes:
            return True
        return bool(self._schemes_for_payload(payload) & schemes)

    def _qdrant_filter_for_schemes(self, schemes: set[str] | None) -> Filter | None:
        if not schemes:
            return None

        sources = sorted(
            {
                src
                for scheme in schemes
                for src in self._sources_by_scheme.get(scheme, set())
            }
        )
        if not sources:
            return None

        conditions = [
            FieldCondition(key="source", match=MatchValue(value=src))
            for src in sources
        ]

        if len(conditions) == 1:
            return Filter(must=conditions)
        return Filter(should=conditions)

    def _retrieval_schemes(self, question: str, search_query: str) -> set[str]:
        # 1. Explicit scheme name/acronym in current question wins.
        current = _detect_explicit_schemes(question)
        if current:
            return current

        # 2. High-precision intent keywords in current question.
        current_intent = _detect_intent_schemes(question)
        if len(current_intent) == 1:
            return current_intent

        # 3. Explicit scheme in history-expanded retrieval query.
        expanded = _detect_explicit_schemes(search_query)
        if expanded:
            return expanded

        # 4. Intent from history-expanded query, only if unambiguous.
        expanded_intent = _detect_intent_schemes(search_query)
        if len(expanded_intent) == 1:
            return expanded_intent

        # Ambiguous/no scheme: search broadly.
        return set()

    def _expand_scheme_query(self, query: str, schemes: set[str]) -> str:
        if not schemes:
            return query

        norm = _scheme_norm(query)
        additions: list[str] = []

        for scheme in sorted(schemes):
            canonical = _SCHEME_CANONICAL_NAME.get(scheme)
            if canonical and not _contains_alias(norm, canonical):
                additions.append(canonical)

            # Add a few aliases too. This helps both dense and BM25.
            for alias in _SCHEME_ALIASES.get(scheme, ())[:4]:
                if not _contains_alias(norm, alias):
                    additions.append(alias)

        if not additions:
            return query

        return f"{query} {' '.join(additions)}".strip()

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

        self._sources_by_scheme = {}
        for p in payloads:
            src = p.get("source")
            if not src:
                continue
            for scheme in self._schemes_for_payload(p):
                self._sources_by_scheme.setdefault(scheme, set()).add(src)

        if payloads:
            self._payload_key_to_index = {
                self._payload_key(p): i for i, p in enumerate(payloads)
            }
            self._bm25 = BM25Okapi(
                [self._bm25_tokenize(self._payload_search_text(p)) for p in payloads]
            )
        else:
            # Fail loud and hard — a silent dense-only fallback masks an un-ingested collection.
            self._bm25 = None
            raise RuntimeError(
                f"Collection {self._cfg.collection_name!r} is EMPTY. "
                "Run the ingest notebook (qna.ipynb) before launching the app."
            )

    def _dense_search(
        self,
        question: str,
        limit: int,
        schemes: set[str] | None = None,
    ) -> list[dict]:
        qvec = self.embed_query(question)
        query_filter = self._qdrant_filter_for_schemes(schemes)

        kwargs = dict(
            collection_name=self._cfg.collection_name,
            query_vector=qvec,
            limit=limit,
            with_payload=True,
        )
        if query_filter is not None:
            kwargs["query_filter"] = query_filter

        try:
            hits = self._qdrant.search(**kwargs)
        except Exception:
            # If server-side payload filtering is unavailable/misconfigured,
            # fall back to a wider dense search and filter client-side.
            if query_filter is None:
                raise
            kwargs.pop("query_filter", None)
            kwargs["limit"] = max(limit, 100)
            hits = self._qdrant.search(**kwargs)

        payloads = [_payload_as_dict(h.payload) for h in hits if h.payload]

        if schemes:
            payloads = [p for p in payloads if self._payload_matches_schemes(p, schemes)]

        return payloads[:limit]

    def _bm25_search(
        self,
        question: str,
        limit: int,
        schemes: set[str] | None = None,
    ) -> list[dict]:
        if self._bm25 is None:
            return []

        scores = self._bm25.get_scores(self._bm25_tokenize(question))

        if schemes:
            candidate_indices = [
                i
                for i, p in enumerate(self._bm25_payloads)
                if self._payload_matches_schemes(p, schemes)
            ]
        else:
            candidate_indices = list(range(len(scores)))

        # IMPORTANT: do not return zero-score lexical hits.
        ranked = [
            i
            for i in sorted(candidate_indices, key=lambda j: scores[j], reverse=True)
            if float(scores[i]) > BM25_MIN_SCORE
        ][:limit]

        return [self._bm25_payloads[i] for i in ranked]

    def _rrf_fuse(
        self, dense: list[dict], lexical: list[dict], top_k: int
    ) -> tuple[list[dict], list[dict]]:
        """README §7C — weighted RRF: score(doc) = Σ lane_weight / (60 + rank).

        Returns (fused_candidates, fuse_debug) — fuse_debug is parallel-indexed
        to fused_candidates and records each one's dense_rank / bm25_rank /
        rrf_score, so a caller can tell "the right chunk never made it into
        this list" (recall failure, upstream of reranking) apart from "it made
        it in but scored low" (visible in _rerank's debug output instead).
        """
        fused: dict[tuple, float] = {}
        payload_by_key: dict[tuple, dict] = {}
        debug_by_key: dict[tuple, dict] = {}

        def _key(p: dict) -> tuple:
            return (p.get("source"), p.get("chunk_index"))

        lanes = (
            ("dense_rank", dense, DENSE_RRF_WEIGHT),
            ("bm25_rank", lexical, BM25_RRF_WEIGHT),
        )
        for rank_field, lane, weight in lanes:
            for rank, payload in enumerate(lane):
                k = _key(payload)
                fused[k] = fused.get(k, 0.0) + weight / (RRF_K + rank)
                payload_by_key[k] = payload
                debug_by_key.setdefault(k, {"dense_rank": None, "bm25_rank": None})[rank_field] = rank

        ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
        fused_docs = [payload_by_key[k] for k, _ in ordered]
        fused_debug = [
            {
                "source": payload_by_key[k].get("source"),
                "section": payload_by_key[k].get("section"),
                "chunk_index": payload_by_key[k].get("chunk_index"),
                "scheme": sorted(self._schemes_for_payload(payload_by_key[k])),
                "dense_rank": debug_by_key[k]["dense_rank"],
                "bm25_rank": debug_by_key[k]["bm25_rank"],
                "rrf_score": round(score, 5),
            }
            for k, score in ordered
        ]
        return fused_docs, fused_debug

    # CHAIN: build the string used FOR RETRIEVAL ONLY from the current question
    # plus the last few user turns. This resolves referential follow-ups
    # ("what about eligibility for it?") that have no retrievable content on
    # their own. The LLM is still asked only the current question elsewhere.
    def _retrieval_query(self, question: str, history: list[str] | None) -> str:
        if not history:
            return question
        recent = [h for h in history[-HISTORY_QUERY_TURNS:] if h and h.strip()]
        if not recent:
            return question
        # Prior turns first (context), current question last (focus).
        return " ".join(recent + [question]).strip()

    def _query_plan(
        self, question: str, history: list[str] | None) -> tuple[str, set[str]]:
        base_query = self._retrieval_query(question, history)
        schemes = self._retrieval_schemes(question, base_query)
        search_query = self._expand_scheme_query(base_query, schemes)
        return search_query, schemes

    def _sort_payloads_by_bm25(self, query: str, payloads: list[dict]) -> list[dict]:
        if self._bm25 is None or not payloads:
            return payloads

        scores = self._bm25.get_scores(self._bm25_tokenize(query))

        def score(payload: dict) -> float:
            idx = self._payload_key_to_index.get(self._payload_key(payload))
            return float(scores[idx]) if idx is not None else 0.0

        return sorted(payloads, key=score, reverse=True)

    def _augment_with_exhaustive_candidates(
        self,
        search_query: str,
        candidates: list[dict],
        fuse_debug: list[dict],
        schemes: set[str],) -> tuple[list[dict], list[dict]]:
        """Because the corpus is small, guarantee that named/recognized schemes
        get an exhaustive chunk pass before reranking.
        """
        if schemes:
            pool = [
                p
                for p in self._bm25_payloads
                if self._payload_matches_schemes(p, schemes)
            ]
            mode = "scheme_exhaustive"
            cap = EXHAUSTIVE_SCHEME_TOP_K
        elif len(self._bm25_payloads) <= SMALL_CORPUS_EXHAUSTIVE_MAX:
            pool = self._bm25_payloads
            mode = "small_corpus_exhaustive"
            cap = SMALL_CORPUS_EXHAUSTIVE_MAX
        else:
            return candidates, fuse_debug

        if not pool:
            return candidates, fuse_debug

        if len(pool) > cap:
            pool = self._sort_payloads_by_bm25(search_query, pool)[:cap]

        seen = {self._payload_key(p) for p in candidates}

        for payload in pool:
            key = self._payload_key(payload)
            if key in seen:
                continue

            candidates.append(payload)
            seen.add(key)

            fuse_debug.append(
                {
                    "source": payload.get("source"),
                    "section": payload.get("section"),
                    "chunk_index": payload.get("chunk_index"),
                    "scheme": sorted(self._schemes_for_payload(payload)),
                    "dense_rank": None,
                    "bm25_rank": None,
                    "rrf_score": None,
                    "candidate_source": mode,
                }
            )

        return candidates, fuse_debug

    def retrieve(
        self, question: str, history: list[str] | None = None) -> tuple[list[dict], list[dict], str, set[str]]:
        """Returns:
        fused_candidates, fuse_debug, search_query_used, scheme_filter_used
        """
        search_query, schemes = self._query_plan(question, history)

        dense_future = self._executor.submit(
            self._dense_search, search_query, DENSE_TOP_K, schemes
        )
        lexical_future = self._executor.submit(
            self._bm25_search, search_query, BM25_TOP_K, schemes
        )

        dense = dense_future.result()
        lexical = lexical_future.result()

        fused, fuse_debug = self._rrf_fuse(dense, lexical, RRF_FUSE_TOP_K)

        fused, fuse_debug = self._augment_with_exhaustive_candidates(
            search_query=search_query,
            candidates=fused,
            fuse_debug=fuse_debug,
            schemes=schemes,
        )

        if schemes:
            for row in fuse_debug:
                row["scheme_filter"] = sorted(schemes)

        return fused, fuse_debug, search_query, schemes

    # ---- README S1 — rerank + README S3 — stable gate score (mean of top-N sigmoids) ----
    def _rerank(
        self, question: str, candidates: list[dict]
    ) -> tuple[list[dict], float, list[dict]]:
        """Returns (ordered_candidates, gate_score, rerank_debug).

        rerank_debug is the reranked candidates' source/section/sigmoid, best
        first — check whether the source/section you expected an answer to
        come from is even in this list, and if so what sigmoid it got. If
        it's missing entirely, the failure is upstream in retrieve()/RRF
        fusion, not here; if it's present but scored low, the passage itself
        (or its chunking) is the problem.
        """
        if not candidates:
            return [], 0.0, []
        if self._reranker is None:
            # Reranker unavailable: keep RRF order, no calibrated score available.
            return candidates, 1.0, []
        subset = candidates[:RERANK_INPUT_TOP_K]
        pairs = [
            (question, self._payload_search_text(c)[:3000])
            for c in subset
        ]
        predict_kwargs = {}
        try:
            import torch
            # Force raw logits. We apply sigmoid ourselves exactly once below.
            predict_kwargs["activation_fct"] = torch.nn.Identity()
        except Exception:
            pass

        # PERF: batch_size=len(pairs) forces one giant forward pass (up to
        # RERANK_INPUT_TOP_K pairs) in a single batch. On CPU this is often
        # SLOWER than chunked batching (memory pressure, no pipelining) and
        # blocks the whole request until the entire batch finishes. A fixed
        # batch size lets sentence-transformers process in manageable chunks.
        _RERANK_BATCH_SIZE = int(os.environ.get("RERANK_BATCH_SIZE", "16"))

        # LAT2-2: score under inference_mode / no_grad. The cross-encoder is only
        # ever used for a forward pass here, so disabling autograd bookkeeping
        # removes pure overhead — the numbers produced are bit-for-bit the same,
        # so the ranking, the top-K, and the S3 gate are all unchanged.
        def _predict(_pairs):
            try:
                return self._reranker.predict(
                    _pairs,
                    batch_size=_RERANK_BATCH_SIZE,
                    show_progress_bar=False,
                    **predict_kwargs,
                )
            except TypeError:
                # Older sentence-transformers fallback (no activation_fct kwarg).
                return self._reranker.predict(
                    _pairs,
                    batch_size=_RERANK_BATCH_SIZE,
                    show_progress_bar=False,
                )

        try:
            import torch
            with torch.inference_mode():
                logits = _predict(pairs)
        except Exception:
            # torch missing or inference_mode unsupported — plain call, same result.
            logits = _predict(pairs)

        scored = sorted(zip(subset, logits), key=lambda t: float(t[1]), reverse=True)
        ordered = [c for c, _ in scored]
        # Any candidates beyond the reranked subset keep their RRF order behind the reranked ones.
        ordered += candidates[RERANK_INPUT_TOP_K:]
        top_sigmoids = [_sigmoid(float(s)) for _, s in scored[:ABSTAIN_SCORE_TOPN]]
        gate_score = sum(top_sigmoids) / len(top_sigmoids)
        rerank_debug = [
            {
                "source": c.get("source"),
                "section": c.get("section"),
                "chunk_index": c.get("chunk_index"),
                "sigmoid": round(_sigmoid(float(s)), 4),
            }
            for c, s in scored
        ]
        return ordered, gate_score, rerank_debug

    def _chat_temperature(self) -> float:
        """PERF: use whichever temperature the endpoint actually accepts,
        decided once (warmup) instead of re-discovered via a failed call
        on every single query."""
        return CHAT_TEMPERATURE if self._temp0_supported else CHAT_TEMPERATURE_FALLBACK

    # ---- README §7E + S1 + S3 + S5 — grounded answer, guarded, with calibrated abstention ----
    def ask(self, question: str, top_k: int = ANSWER_TOP_K, stream: bool = False,
            history: list[str] | None = None, debug: bool = False):
        """Returns (answer, sources, gate_score) when stream=False,
        or (token_generator, meta_callback) when stream=True, where
        meta_callback() -> {"sources": [...], "gate_score": float, "debug": dict|None}.

        gate_score is the calibrated confidence (README S3) — None when no
        reranker is loaded, so the UI can distinguish "low confidence" from
        "confidence not computed" instead of showing a fake number.

        DEBUG: pass debug=True (streaming path only) to get meta["debug"] =
        {"gate_score_raw", "abstain_threshold", "fused_candidates", "reranked"}
        — fused_candidates shows what survived RRF fusion (dense_rank/
        bm25_rank/rrf_score per chunk); reranked shows the reranker's sigmoid
        per chunk it actually scored. If the source/section you expected is
        missing from fused_candidates entirely, that's a retrieval recall
        failure (RRF fusion / chunking); if it's present but low-sigmoid in
        reranked, that's a passage-quality/chunking problem instead. debug is
        None on every return when debug=False, at zero extra cost.

        CHAIN: `history` is an optional list of PRIOR user-turn strings (oldest
        to newest). It is used only to expand the retrieval query for
        referential follow-ups. The LLM is always asked only `question`.
        """
        # README S5 — PII redaction on the query itself, before it touches embedding
        # or chat APIs at all (not just at display time).
        question = redact_pii(question)

        # Input validation: guard degenerate inputs before spending any API calls.
        # Empty/whitespace-only submits and pathologically long pastes shouldn't
        # reach retrieval or the LLM. Treated as a clean refusal, not a crash.
        stripped = question.strip()
        if not stripped:
            if not stream:
                return REFUSAL_STRING, [], None
            return iter([REFUSAL_STRING]), (lambda: {"sources": [], "gate_score": None, "debug": None})
        if len(stripped) > 4000:
            # Truncate rather than reject outright — keep the leading, most
            # topical portion so a long paste still has a chance to retrieve.
            question = stripped[:4000]

        # README S5 — jailbreak/injection filter, run BEFORE retrieval, blocks on a hit.
        if is_jailbreak_attempt(question):
            if not stream:
                return JAILBREAK_BLOCK_STRING, [], None
            return iter([JAILBREAK_BLOCK_STRING]), (lambda: {"sources": [], "gate_score": None, "debug": None})

        # CHAIN: redact prior turns too, then hand them to retrieval only.
        clean_history = [redact_pii(h) for h in history] if history else None
        fused, fuse_debug, search_query, debug_schemes = self.retrieve(
            question, history=clean_history
        )
        if not fused:
            no_hits_debug = {
                "reason": "no candidates survived retrieval/RRF fusion",
                "retrieval_query": search_query,
                "scheme_filter": sorted(debug_schemes),
            } if debug else None
            if not stream:
                return REFUSAL_STRING, [], None
            return iter([REFUSAL_STRING]), (lambda: {"sources": [], "gate_score": None, "debug": no_hits_debug})

        # Rerank using the expanded retrieval query, not only the current short question.
        # This fixes follow-ups like: "What about eligibility for it?"
        ranked, gate_score, rerank_debug = self._rerank(search_query, fused)
        # None-able gate score for display: the reranker returns a sentinel 1.0 when
        # it isn't loaded (see _rerank) — that isn't a real calibrated score, so don't
        # surface it as one.
        display_gate_score = gate_score if self._reranker is not None else None

        # DEBUG: built once here so every return path below (abstain or
        # answer) can attach the same diagnostic snapshot.
        debug_info = None
        if debug:
            debug_info = {
                "retrieval_query": search_query,
                "scheme_filter": sorted(debug_schemes),
                "gate_score_raw": gate_score,
                "abstain_threshold": ABSTAIN_THRESHOLD,
                "fused_candidates": fuse_debug,
                "reranked": rerank_debug,
            }

        # README S3 — abstain only when confidence is CLEARLY low (stable mean-of-top-N gate).
        if self._reranker is not None and gate_score < ABSTAIN_THRESHOLD:
            if not stream:
                return REFUSAL_STRING, [], display_gate_score
            return iter([REFUSAL_STRING]), (lambda: {"sources": [], "gate_score": display_gate_score, "debug": debug_info})

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
            # CONTEXT: cap each block handed to the LLM at CONTEXT_CHAR_BUDGET so a
            # single long chunk can't blow up prompt tokens. Mirrors the UI [:1200]
            # cap above; does not change which chunks are chosen or their order.
            budgeted = body[:CONTEXT_CHAR_BUDGET] + ("…" if len(body) > CONTEXT_CHAR_BUDGET else "")
            blocks.append(f"{tag}\n{budgeted}")
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
            self._corrective_retry_count += 1
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
                    model=self._cfg.chat_model, messages=retry_messages,
                    temperature=self._chat_temperature(),
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
                # PERF: use whichever temperature already proved to work (see
                # _warmup / _chat_temperature) instead of trying temp=0 fresh
                # on every request and eating a failed round trip when it's
                # known to be rejected.
                temp = self._chat_temperature()
                try:
                    resp = self._chat_openai.chat.completions.create(
                        model=self._cfg.chat_model, messages=messages,
                        temperature=temp, stream=True,
                    )
                except Exception:
                    if temp != CHAT_TEMPERATURE_FALLBACK:
                        self._temp0_supported = False
                        resp = self._chat_openai.chat.completions.create(
                            model=self._cfg.chat_model, messages=messages,
                            temperature=CHAT_TEMPERATURE_FALLBACK, stream=True,
                        )
                    else:
                        raise
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

            return _gen(), (lambda: {"sources": sources, "gate_score": display_gate_score, "debug": debug_info})

        temp = self._chat_temperature()
        try:
            completion = self._chat_openai.chat.completions.create(
                model=self._cfg.chat_model, messages=messages, temperature=temp,
            )
        except Exception as e_zero:
            if temp != CHAT_TEMPERATURE_FALLBACK:
                print(f"temperature={temp} rejected ({e_zero}); retrying at {CHAT_TEMPERATURE_FALLBACK}.")
                self._temp0_supported = False
                try:
                    completion = self._chat_openai.chat.completions.create(
                        model=self._cfg.chat_model, messages=messages, temperature=CHAT_TEMPERATURE_FALLBACK,
                    )
                except Exception as e_fb:
                    raise RuntimeError(f"MaaS chat call failed at both temperatures: {e_fb}") from e_fb
            else:
                raise RuntimeError(f"MaaS chat call failed: {e_zero}") from e_zero

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
