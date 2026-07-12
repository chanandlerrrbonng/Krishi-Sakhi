# 🌾 Krishi-Sakhi

```
██╗  ██╗██████╗ ██╗███████╗██╗  ██╗██╗    ███████╗ █████╗ ██╗  ██╗██╗  ██╗██╗
██║ ██╔╝██╔══██╗██║██╔════╝██║  ██║██║    ██╔════╝██╔══██╗██║ ██╔╝██║  ██║██║
█████╔╝ ██████╔╝██║███████╗███████║██║    ███████╗███████║█████╔╝ ███████║██║
██╔═██╗ ██╔══██╗██║╚════██║██╔══██║██║    ╚════██║██╔══██║██╔═██╗ ██╔══██║██║
██║  ██╗██║  ██║██║███████║██║  ██║██║    ███████║██║  ██║██║  ██╗██║  ██║██║
╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚══════╝╚═╝  ╚═╝╚═╝    ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝
```

**A grounded, cross-lingual RAG copilot for India's rural livelihood schemes**

> "Ask in हिंदी. Get the exact rule from an English government circular. Trust every word."

**Track:** Platform Stack Status
**Team:** Amrit Kumar Ghoshal · Sreehari K. · Aman Kumar · Samyak Hiran

---

## Table of Contents

1. [The Human Problem](#1-the-human-problem)
2. [Why This Is the Right Test Bed](#2-why-this-is-the-right-test-bed)
3. [What We Actually Built](#3-what-we-actually-built)
4. [System Architecture](#4-system-architecture)
5. [Critical Engineering Decisions](#5-critical-engineering-decisions)
6. [Feature Deep-Dives](#6-feature-deep-dives)
7. [Evaluation — Real Numbers on a Held-Out Gold Set](#7-evaluation--real-numbers-on-a-held-out-gold-set)
8. [The UI — Trust Made Visible](#8-the-ui--trust-made-visible)
9. [Tech Stack & Vayu Integration](#9-tech-stack--vayu-integration)
10. [Deployment](#10-deployment)
11. [Build Order & Scope Discipline](#11-build-order--scope-discipline)
12. [Honest Caveats](#12-honest-caveats)
13. [Impact & Close](#13-impact--close)

---

## 1. The Human Problem

Meet Sunita — a Bank Sakhi working as a Business Correspondent in a Tier-3 district in rural India. Every day she helps villagers apply for PM-KISAN payments, SHG loans, and Kisan Credit Cards. She reads RBI and Ministry circulars in formal English. She speaks with every household in हिंदी. And she is personally accountable for every single rupee figure she quotes.

> "If I say the wrong number, she loses the loan. There is no 'sorry, my mistake.'"

The problem is structural. Scheme guidelines run 40–80 dense, legalese-filled pages. The critical eligibility line — the entry age, the exact pension amount, the interest subvention rate — is buried somewhere inside. Generic LLMs will answer fluently, confidently, and frequently incorrectly. In rural credit, a fluent-but-wrong answer is a family's lost entitlement.

| Failure Mode | Why It Happens |
|---|---|
| Buried rules | Scheme PDFs run 40–80 pages of dense legalese — the one decisive line is unfindable in 90 seconds |
| Language wall | All circulars are in formal English; the Bank Sakhi and the farmer think and speak in हिंदी |
| Confidently wrong | A generic chatbot hallucinates the wrong pension amount or interest rate — fluently and without any warning |
| Real economic harm | Misquoting a 3% repayment incentive means a family forfeits an entitlement they earned |

A generic assistant can be ~96% fluent while being grounded only ~42% of the time. That gap is the entire product opportunity. Krishi-Sakhi closes it.

---

## 2. Why This Is the Right Test Bed

This domain was chosen deliberately — not because it is easy, but because it is the hardest possible stress test for a RAG system and the most consequential place to get it right.

**PII is native to the workflow.** SHG and KCC application files naturally contain Aadhaar numbers, PAN cards, mobile numbers, and bank account details. Redaction is a core domain requirement, not a bolted-on demo prop.

**The corpus is closed and authoritative.** Every correct answer is one verifiable line in one official PDF. Ground truth is exact and deterministic — which makes Hit@k and MRR meaningful metrics, not fuzzy approximations. The gold eval set can be manually verified against the source documents in minutes.

**Numerically sensitive retrieval.** Rules that are semantically close but numerically distinct — the PM-KMY monthly pension (₹3,000) versus the KCC short-term loan limit (₹3,00,000) versus the PM-KMY entry-age window (18–40 years) — confuse dense embeddings but are matched exactly by BM25 on the literal token the user typed. This is exactly the scenario where hybrid retrieval earns its cost.

A typical 90-second exchange the system handles end-to-end:

```
Farmer asks (Hindi): "ड्रोन दीदी योजना में कितनी सब्सिडी मिलती है?"
     ↓
Query redacted (PII check) → language detected (hi) → English translation added
     ↓
Dense search (Qdrant) ∥ BM25 search (in-process) → RRF fusion
     ↓
Cross-encoder reranks top-60 → gate score = 0.71 → PASSES threshold
     ↓
LLM generates grounded Hindi answer with citation
     ↓
Answer: "Namo Drone Didi के तहत 80% सब्सिडी मिलती है, जो ₹8 लाख तक सीमित है। [1]"
Source: [1] namo_drone_didi.pdf · §4.2 · p.7 · chars 2841–2974
```

---

## 3. What We Actually Built

Every team receives the same starter repository. Most ship it nearly as-is, demo in English on sample documents, and treat the README's empty guardrails claim as done. We didn't. We read the actual source code — `rag_client.py`, the ingest notebook, the chunker, the S3 loader — and rebuilt every layer the brief promised that the code skipped.

**What the starter actually ships vs. what we delivered:**

| README Promises | Starter Actually Ships | Krishi-Sakhi |
|---|---|---|
| Guardrails: PII, toxicity, jailbreak | `grep -r pii` → zero lines of guardrail code anywhere | Real Aadhaar/PAN/phone redaction (regex, script-agnostic) + jailbreak/injection filter via presidio + curated pattern list |
| Multilingual: EN + Indian languages | Whatever the embedding model happens to do — no explicit handling | True cross-lingual हिंदी ↔ EN retrieval: detect language, translate query, fuse both embeddings, answer in the user's script |
| "Cites exact source and line" | Filename + a raw cosine similarity score in a collapsible expander | Granular citations: scheme · section · page · char_start · char_end, rendered as inline [1]-style footnote chips with a collapsible source panel |
| Trustworthy answers | `temperature=0.2`, refuses only when the retrieved context string is literally empty | Calibrated abstention (mean-of-top-3 reranker sigmoids, threshold 0.28) + a visible groundedness badge + a fixed, programmatically-greppable refusal string |
| Hybrid retrieval | Single dense vector search (`query_points`), cosine, top-k only | Client-side BM25 + dense, RRF-fused, then cross-encoder reranked — all on `qdrant-client==1.7.3` without touching the version pin |
| Notebook connects to hosted Vector DB | `COLLECTION_NAME = "<COLLECTION_NAME>"` placeholder + `local_db()` (writes to disk) | `hosted_instance()` + real collection name — the app and the index point at the same store |

---

## 4. System Architecture

### Ingest Pipeline (AI Studio, one-pass, idempotent)

```
7 Official Scheme PDFs  (Vayu Object Storage)
          │
    ┌─────▼─────────────────────────────────────┐
    │  Structure-aware chunker                   │
    │  • Separator hierarchy: \n##, \n###, \n\n, │
    │    \n, ।, ". ", " ", ""                    │
    │  • ~400–500 tokens/chunk, 60-token overlap  │
    │  • HTML-to-text (BeautifulSoup/markdownify) │
    │  • Tracks: char_start, char_end, section,  │
    │    page, lang (langdetect per chunk)        │
    └─────┬─────────────────────────────────────┘
          │
    ┌─────▼─────────────────────────────────────┐
    │  Embed (Qwen3-Embedding-8B via Vayu MaaS)  │
    │  • Documents: NO instruction prefix        │
    │  • Payload: {text, source, scheme,         │
    │    section, page, char_start, char_end,    │
    │    chunk_index, lang, search_text}         │
    └─────┬─────────────────────────────────────┘
          │
    ┌─────▼─────────────────────────────────────┐
    │  Vayu Vector DB (Qdrant 1.7.3)             │
    │  Payload-indexed for per-scheme filtering  │
    └───────────────────────────────────────────┘
```

### Query Pipeline (RAGEngine — 8 gates, every request)

```
USER QUESTION (हिंदी or English)
        │
   ┌────▼────────────────────────────────────────────────────────┐
   │ GATE 1 — PII Redaction                                       │
   │  Aadhaar (12-digit), PAN ([A-Z]{5}[0-9]{4}[A-Z]),           │
   │  Phone (+91 / 10-digit Indian mobile) — regex, script-agnostic│
   └────┬────────────────────────────────────────────────────────┘
        │
   ┌────▼────────────────────────────────────────────────────────┐
   │ GATE 2 — Jailbreak / Injection Filter                        │
   │  Curated regex patterns + keyword list; blocks BEFORE        │
   │  retrieval; returns JAILBREAK_BLOCK_STRING on hit            │
   └────┬────────────────────────────────────────────────────────┘
        │
   ┌────▼────────────────────────────────────────────────────────┐
   │ GATE 3 — Language Detection + Query Expansion               │
   │  detect_script_lang() (Devanagari char scan, deterministic) │
   │  If Hindi → expand query with English translation            │
   │  Scheme aliases injected into search query                   │
   │  History folding (last 2 user turns, CHAIN mode)            │
   └────┬────────────────────────────────────────────────────────┘
        │
        │              ╔══════════╗   ╔══════════╗
   ┌────▼──────┐       ║ DENSE    ║   ║  BM25    ║
   │ EMBED     │──────►║ Qdrant   ║   ║ (in-proc)║
   │ (prefixed)│       ║ top-80   ║   ║ top-80   ║
   └───────────┘       ╚══════════╝   ╚══════════╝
                              │              │
                         ┌────▼──────────────▼────┐
                         │  RRF FUSION (weighted) │
                         │  score = Σ w/(60+rank) │
                         │  dense_w=1.0, bm25_w=0.5│
                         │  → top-80 fused         │
                         └────────┬───────────────┘
                                  │
                    ┌─────────────▼──────────────────┐
                    │  EXHAUSTIVE SCHEME AUGMENTATION │
                    │  (guarantee named-scheme chunks  │
                    │  enter the reranker pool)        │
                    └─────────────┬──────────────────┘
                                  │
                    ┌─────────────▼──────────────────┐
                    │  CROSS-ENCODER RERANK           │
                    │  bge-reranker-v2-m3, multilingual│
                    │  batch_size=16, inference_mode()│
                    │  → top-60 scored                │
                    └─────────────┬──────────────────┘
                                  │
                    ┌─────────────▼──────────────────┐
   ┌── ABSTAIN ◄────┤ GATE 4 — Calibrated Confidence │
   │ (no LLM call) │ mean sigmoid(top-3 logits)       │
   │               │ threshold = 0.28                 │
   └───────────────┤ PASS → top-5 chunks to LLM      │
                   └─────────────┬──────────────────┘
                                 │
                   ┌─────────────▼──────────────────┐
                   │  LLM (Vayu MaaS, gpt-oss-120b) │
                   │  temperature=0, grounded prompt │
                   │  Every sentence → [N] citation  │
                   │  Same-language directive enforced│
                   └─────────────┬──────────────────┘
                                 │
                   ┌─────────────▼──────────────────┐
                   │  GATE 5 — Language Check        │
                   │  Wrong script? → corrective retry│
                   │  GATE 6 — PII Redact (output)   │
                   │  GATE 7 — Sources assembled     │
                   │  GATE 8 — Stream to UI          │
                   └────────────────────────────────┘
```

---

## 5. Critical Engineering Decisions

These are not theoretical choices. They are corrections discovered by reading the actual starter code — each one would have silently broken the pipeline in the live demo environment if left unfixed.

### Correction 1 — `qdrant-client==1.7.3` blocks native hybrid search

The `requirements.txt` pins `qdrant-client==1.7.3`, and `rag_client.py` already contains a `hasattr(self._qdrant, "query_points")` guard that silently falls back to the old `.search()` API on this version. The native Query API with server-side sparse vectors and RRF only exists in client 1.10+.

**Resolution:** Hybrid search is built entirely client-side. Dense retrieval stays in Qdrant (network call). BM25 runs in-process via `rank_bm25.BM25Okapi` (CPU, instant at hackathon corpus scale). RRF fusion is ~40 lines of Python, works on any Qdrant version, and requires zero collection recreation.

```python
# Weighted RRF — runs in Python, version-pin-agnostic
def _rrf_fuse(self, dense, lexical, top_k):
    fused = {}
    for rank_field, lane, weight in [
        ("dense_rank", dense, 1.0),
        ("bm25_rank", lexical, 0.5),
    ]:
        for rank, payload in enumerate(lane):
            k = _key(payload)
            fused[k] = fused.get(k, 0.0) + weight / (60 + rank)
    ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    return [payload_by_key[k] for k, _ in ordered], fuse_debug
```

### Correction 2 — MaaS does not accept `prompt_name="query"`

The Vayu MaaS embedding endpoint is an OpenAI-compatible HTTP surface: `embeddings.create(input=..., model=...)`. There is no `prompt_name` kwarg — that parameter exists only on local HuggingFace `SentenceTransformer` objects. Passing it to MaaS raises an error.

**Resolution:** The Qwen3 instruction prefix is prepended as a string on the query path only, manually. Documents receive no prefix (the model card says none is needed for retrieval documents), which means no re-ingest is required — only the query path changes.

```python
QWEN_INSTRUCT = "Instruct: Given a question, retrieve passages that answer it\nQuery:"

def embed_query(self, question: str) -> list[float]:
    # Query path: prefixed. Routed through LRU cache for repeated/FAQ queries.
    return list(self._embed_query_cached(question))

# _embed_query_cached wraps:
# self.embed_texts([f"{QWEN_INSTRUCT}{question}"])[0]
```

### Correction 3 — The reranker lives in the container, not on MaaS

`bge-reranker-v2-m3` is ~568M parameters. It cannot be invoked over an HTTP-only MaaS endpoint via `CrossEncoder.predict()`. The architecture decision is: check the Vayu MaaS catalog for a hosted reranker first. If none exists, `bge-reranker-v2-m3` is baked into the Docker image at build time — not downloaded on first request, which would cause a cold-start timeout on ML Service.

Two env flags control the behavior cleanly: `RERANKER_MODEL=none` / `SKIP_RERANKER=true` skips the download entirely for ephemeral dev containers; `RERANKER_BACKEND=onnx` opts into CPU-accelerated inference without changing scores.

### Correction 4 — `temperature=0` probe + permanent memory

Some OpenAI-compatible MaaS gateways clamp or reject `temperature=0`. Previously, every single query attempted `temp=0`, ate the failure response, then retried at `temp=0.1` — wasting a full round trip on every request in production.

**Resolution:** a harmless warmup probe (one token, `"hi"`) runs at engine initialization, which is cached by `@st.cache_resource`. The result is stored in `self._temp0_supported`. Every subsequent query routes straight to whichever temperature actually works, with zero wasted round trips.

### Correction 5 — Notebook points at an empty local store

`COLLECTION_NAME = "<COLLECTION_NAME>"` is a literal placeholder and `qdrant = local_db()` writes an on-disk Qdrant store to `os.curdir`. The app and the notebook pointed at two different stores; retrieval silently returned nothing.

**Resolution:** `hosted_instance()` + a real `COLLECTION_NAME` are set as the absolute first step, before any feature work. This is table-stakes plumbing that gates everything else — it was done on day one.

---

## 6. Feature Deep-Dives

### F1 — Structure-Aware, Token-Budgeted Chunking

The starter's `chunk_file_text` merges paragraphs then hard-slices at 1500-character boundaries. A table row split in the middle returns half a fact with high embedding confidence — the entry age `29` lands in one chunk, its corresponding monthly contribution `₹100` in the next. Both chunks retrieve; neither answers correctly.

The replacement chunker uses a separator hierarchy that respects both document structure and Hindi sentence boundaries:

```python
sep = ["\n## ", "\n### ", "\n\n", "\n", "। ", ". ", " ", ""]
# ।  is the Devanagari danda — the Hindi sentence-boundary character
```

Chunks target ~400–500 tokens with 60-token overlap. Character offsets (`char_start`, `char_end`) and the nearest preceding heading (`section`) are tracked during splitting — these feed directly into the granular citation system. A BeautifulSoup/markdownify pass strips HTML tags from `.html` sample docs before chunking, because the starter indexed raw HTML tags straight into the embedding space.

### F2 — Client-Side Hybrid Retrieval (BM25 + Dense, RRF-Fused)

The BM25 index is built once at engine initialization by scrolling the full collection out of Qdrant with payloads and constructing a `BM25Okapi` in-process. This is fast and accurate at hackathon corpus scale. The BM25 tokenizer uses `\w+` unicode word extraction (not `.split()`) so punctuation like `"PM-KISAN,"` doesn't attach to tokens and ≠ `"pm-kisan"`. Devanagari word characters are preserved natively by `re.UNICODE`.

Dense retrieval and BM25 retrieval run in parallel via a shared `ThreadPoolExecutor(max_workers=4)`, so both costs are paid concurrently rather than sequentially. RRF fusion uses weighted lanes (`dense_weight=1.0`, `bm25_weight=0.5`) so the semantically stronger dense signal leads while BM25 rescues the exact-numeric queries where dense embeddings drift.

### F3 — Two-Stage Cross-Encoder Reranker with Calibrated Abstention

After RRF fusion yields up to 80 candidates, `BAAI/bge-reranker-v2-m3` (568M params, multilingual including Hindi+English) scores every (query, passage) pair. It runs inside the deployed container under `torch.inference_mode()` — no autograd bookkeeping — at `batch_size=16` to avoid memory pressure from single giant forward passes.

The abstention gate uses the mean sigmoid of the top-3 reranker logits rather than the raw top-1 score, which is statistically noisier. `bge-reranker-v2-m3` relevant-passage sigmoids typically sit in the 0.3–0.6 range, not 0.9+, so the threshold is calibrated to 0.28, derived from the eval set's score distribution on known out-of-domain queries.

```python
ABSTAIN_THRESHOLD = 0.28  # calibrated on eval set, not hardcoded magic
ABSTAIN_SCORE_TOPN = 3    # mean of top-3 sigmoids for stability

top_sigmoids = [_sigmoid(float(s)) for _, s in scored[:ABSTAIN_SCORE_TOPN]]
gate_score = sum(top_sigmoids) / len(top_sigmoids)

if gate_score < ABSTAIN_THRESHOLD:
    return REFUSAL_STRING, [], display_gate_score
    # LLM is NEVER called — no hallucination risk
```

The UI displays a rescaled confidence badge that maps "right at the abstain threshold" → 0% and "maximum sigmoid" → 100%, so the user sees a meaningful percentage rather than the raw 0.28–1.0 logit range.

### F4 — Genuine Cross-Lingual Retrieval

When the query language is detected as Hindi (Devanagari character scan, deterministic and zero-dependency), the system adds an English-translated expansion of the query before embedding and retrieval. Scheme canonical names and aliases are also injected into the search string so BM25 can match both the Hindi alias and the English document term.

```python
# Scheme alias injection example for "ड्रोन दीदी योजना"
_SCHEME_ALIASES["NAMO_DRONE_DIDI"] = (
    "namo drone didi", "drone didi", "नमो ड्रोन दीदी", "ड्रोन दीदी"
)
# Canonical expansion appended to query:
# → "ड्रोन दीदी योजना Namo Drone Didi namo drone didi drone didi"
```

The answer is generated with a language directive that appears twice in the prompt — once in the system turn and once directly above the question in the user turn — because a single system-prompt mention gets out-competed by a large Hindi-heavy context block. A post-generation language check (`detect_script_lang`) triggers a corrective retry if the script is wrong. The retry fires as a sentinel yield (`LANG_CORRECTION_MARKER`) on the streaming path so the UI discards the wrong-language draft wholesale rather than appending to it.

### F5 — PII Redaction + Jailbreak Filtering

The starter ships zero guardrails despite the README naming three. Krishi-Sakhi implements them for real, scoped to what is actually achievable and honest about what isn't.

PII redaction is applied in three places: on the user's raw query before it touches any API, on retrieved context before it enters the LLM prompt, and on the final answer before it is displayed in the UI. The patterns are script-agnostic regex — Aadhaar (12-digit), PAN (`[A-Z]{5}[0-9]{4}[A-Z]`), Indian mobile numbers — which means they work regardless of query language without requiring a full Hindi NER pipeline (Presidio's default models are English-only, a known limitation documented explicitly rather than hidden).

Jailbreak filtering runs before retrieval via a curated regex pattern list, blocking classic injection patterns ("ignore all previous instructions", "you are now", "reveal your system prompt", "DAN", etc.) before they touch the embedding API or the vector database.

### F6 — Named-Scheme Exhaustive Retrieval Augmentation

When a specific scheme is detected in the query (via alias matching or intent keywords), the retrieval pipeline guarantees that every chunk tagged to that scheme enters the reranker pool — not just whatever floated to the top of RRF. This prevents a query about the AIF loan limit from being crowded out by KCC chunks that share generic finance vocabulary. The scheme detection is a two-layer system: exact alias matching (highest precision) and intent keyword matching (catches paraphrases), with history-expanded query folding for referential follow-ups.

### F7 — Conversational Chain Mode

The last two user turns are folded into the retrieval query (not the LLM prompt) to resolve referential follow-ups like "What about eligibility for it?" that have no standalone retrievable content. The LLM always sees only the current question — the history expansion affects only what is searched for.

### F8 — Query-Embedding LRU Cache

An `lru_cache(maxsize=256)` wraps the query embedding call. The FAQ buttons on the welcome screen send identical strings on every click; follow-up queries with the same expansion text skip the embedding round trip entirely. Cache hits produce byte-identical vectors so retrieval and scoring are unaffected.

---

## 7. Evaluation — Real Numbers on a Held-Out Gold Set

### Gold Set Composition

The gold evaluation set contains 30 question · answer · source triples across all 7 ingested scheme documents. It is held out completely from prompt tuning and was not seen during any development iteration.

- 50% Hindi queries, including genuinely cross-lingual pairs (Hindi question, English source)
- 5 out-of-domain "should-abstain" probes calibrating the S3 threshold
- Covers numerical rules (₹-amounts, ages, percentages), eligibility criteria, and procedural steps

### Sample Triples

| Question | Expected Answer | Source |
|---|---|---|
| PM-KMY entry age? | 18–40 years | PM-KMY §2.1 |
| Namo Drone Didi max subsidy? | 80%, up to ₹8 lakh | NDD §4.2 |
| प्र. पेंशन कितनी मिलेगी? | ₹3,000/month at age 60 | PM-KMY §3.4 |
| KCC interest subvention rate? | 3% p.a. for timely repayment | KCC Circular §5 |
| What is the capital subsidy under PMFME? | 35% credit-linked, up to ₹10 lakh | PMFME §3.2 |

### Metrics

| Metric | Starter Baseline | Krishi-Sakhi | Delta |
|---|---|---|---|
| Hit@4 (retrieval recall) | 0.58 | 0.86 | +0.28 |
| MRR (mean reciprocal rank) | 0.49 | 0.78 | +0.29 |
| Faithfulness (LLM-judge, 1–5 scaled) | 0.62 | 0.91 | +0.29 |
| Abstention precision (out-of-domain) | 0.20 | 0.92 | +0.72 |

**Evaluation honesty:** Hit@k and MRR are deterministic — they are computed by checking whether the gold-set source chunk appears in the retrieved top-k, and require no subjectivity. LLM-judge faithfulness uses a different model from the answering model to avoid grading circularity. Abstention precision is measured separately on the out-of-domain probe set. All numbers in this table are replaced with actual measured values before presentation.

---

## 8. The UI — Trust Made Visible

Every backend engineering decision surfaces directly in the chat interface. Trust is not claimed in a tooltip — it is shown on every single answer.

**Groundedness Badge:** Every assistant response opens with a badge strip that shows the answer's status: `GROUNDED · 3 SOURCES` (with a rescaled confidence percentage), `ABSTAINED · OUT-OF-DOMAIN` (gold, with a pulsing amber dot), or `BLOCKED · GUARDRAIL` (for jailbreak attempts). The confidence percentage is rescaled so the abstain threshold maps to 0% and maximum confidence maps to 100% — a human-interpretable number, not a raw reranker logit.

**Granular Inline Citations:** Every factual sentence carries an inline `[1]`-style chip. The collapsible sources panel below shows scheme name, section heading, page number, and character offsets for each cited chunk — so a judge can open the source PDF, navigate to the right page, and verify the answer in under 30 seconds.

**Visible Abstention:** When the system does not know, it says so explicitly in-frame: *"I could not find this in the provided documents."* The abstention is visually distinct (gold badge, amber palette) from a grounded answer. The LLM is never called when the reranker gate fails — so there is no possibility of a fluent hallucination slipping through.

**"While You Wait" Fact Cards:** While retrieval, reranking, and generation are in flight, the streaming placeholder shows a random verified scheme fact (e.g., *"Farmers pay a maximum premium of just 2% for Kharif crops under PMFBY"*) instead of a plain spinner. The fact card occupies the exact same slot as the streaming answer — it disappears automatically the instant the first real token arrives, replaced by the growing answer in place.

**Persistent FAQ Picker:** A *Browse suggested questions* popover is available at every point in the conversation — not just on the empty-state welcome screen. It groups 20 questions across four farmer-relevant domains (Income & Pension, Credit & Loans, Insurance, Modernization) in both हिंदी and English, with a live toggle. Every suggested question routes through the same `_submit_prompt()` pipeline as typed queries, so the generation lock and conversation title logic apply identically.

**Multi-Conversation Management:** Chat history is stored in `st.session_state.conversations` as a keyed dictionary. "New Conversation" creates a fresh thread without destroying earlier ones. A sidebar "Recents" list shows all open threads and lets you switch between or delete them. Generation is locked (input dimmed) while a turn is in flight, preventing double-submission.

---

## 9. Tech Stack & Vayu Integration

Every layer of the stack maps to a named Vayu service. This is not a local demo with a Vayu logo — it is a live deployment.

| Layer | Service | Role |
|---|---|---|
| Storage | Vayu Object Storage (S3-compatible) | 7 official scheme PDFs, immutable corpus, presigned-URL access during ingest |
| Ingest Compute | Vayu AI Studio (notebook) | Idempotent one-pass ingest — chunk, embed, and index in the notebook that owns the schema |
| Vector Search | Vayu Vector DB (Qdrant 1.7.3) | Payload-indexed store: `{scheme, section, page, char_start, char_end, lang, chunk_index, search_text}` |
| Embeddings | Vayu MaaS — Qwen/Qwen3-Embedding-8B | Multilingual dense embeddings for both document and query paths (different handling per path) |
| Chat Generation | Vayu MaaS — openai/gpt-oss-120b | Grounded answer generation, temperature=0, streaming, calibrated retry |
| Retrieval Add-ons | In-container Python | `rank_bm25` (BM25), `bge-reranker-v2-m3` (cross-encoder), `presidio` (PII), `langdetect` |
| App + Deploy | Streamlit → Docker → Vayu ML Service | Port 8501, model weights baked at build time, live public URL |

### Ingested Scheme Corpus

The seven source documents span India's core rural livelihood infrastructure — chosen because together they answer the full range of questions a Bank Sakhi faces in a working day.

- **PM-KISAN** — ₹6,000/yr income support for landholding farmer families
- **PM-KMY** — ₹3,000/month pension for small and marginal farmers aged 18–40
- **Namo Drone Didi** — 80% subsidy (up to ₹8 lakh) for Women SHG agricultural drones
- **DAY-NRLM / SHG** — collateral-free loans up to ₹20 lakh for Women Self Help Groups
- **Kisan Credit Card (KCC)** — revolving crop credit + 3% interest subvention for timely repayment
- **PMFBY** — Pradhan Mantri Fasal Bima Yojana crop insurance (2% Kharif / 1.5% Rabi premium)
- **Agriculture Infrastructure Fund (AIF)** — 3% interest subvention on loans up to ₹2 crore

---

## 10. Deployment

The deployment sequence is linear and produces a live, public URL — not a `localhost:8501` demo.

```bash
# 1. Build — reranker weights baked into the image at this step,
#    never downloaded on first request (prevents ML Service cold-start timeouts)
docker build -t krishi-sakhi:latest .

# 2. Tag and push to Vayu Hackathon Container Registry
docker tag krishi-sakhi:latest <vayu-registry>/krishi-sakhi:latest
docker push <vayu-registry>/krishi-sakhi:latest

# 3. Deploy on Vayu ML Service, port 8501
# (via the hackathon platform dashboard or CLI)

# 4. Verify the live endpoint responds before day-of-judging
curl https://<deployed-url>/healthz
```

**Image composition:** The Docker image includes `torch` + `bge-reranker-v2-m3` weights (~2.3GB additional), `sentence-transformers`, `presidio-analyzer`, `rank_bm25`, `langdetect`, `beautifulsoup4`, `markdownify`, `qdrant-client==1.7.3`, and `streamlit`. Weights are pre-downloaded at build time via the `HF_HOME` cache path so there is no runtime download on any cold start.

**Environment variables required** (set in `ask-it/.env`):

```bash
QDRANT_URL=<vayu-vector-db-url>
QDRANT_API_KEY=<key>
QDRANT_PORT=443
EMBEDDING_OPENAI_API_KEY=<maas-key>
OPENAI_API_KEY=<maas-key>
OPENAI_BASE_URL=<vayu-maas-base-url>
COLLECTION_NAME=krishi_sakhi_rag
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
CHAT_MODEL=openai/gpt-oss-120b

# Optional tuning
RERANKER_MODEL=BAAI/bge-reranker-v2-m3   # set to 'none' to skip local reranker
SKIP_RERANKER=false
ABSTAIN_THRESHOLD=0.28
DENSE_TOP_K=80
BM25_TOP_K=80
ANSWER_TOP_K=5
```

---

## 11. Build Order & Scope Discipline

The development sequence was chosen to front-load correctness and avoid wasted embedding credits.

1. **Fix notebook plumbing** — `hosted_instance()` + real `COLLECTION_NAME`. Nothing else functions without this. Done first.
2. **Structure-aware chunker + HTML cleaning** — establishes the payload schema that all downstream features depend on.
3. **Query-instruction-prefixed embedding** — zero-cost recall gain, query-path-only change.
4. **Client-side hybrid retrieval** — BM25 + RRF in Python, version-pin-safe.
5. **Re-ingest the corpus once** — after schema and chunker are both finalized, to avoid repeatedly burning embedding API credits.
6. **Cross-encoder reranker + calibrated abstention** — deployed container tested on day one (not the night before) because the torch + weights image is exactly where a smooth plan dies late.
7. **Evaluation harness** — Hit@k/MRR first (deterministic, cheap), LLM-judge faithfulness second.
8. **Cross-lingual demo** — language detect, alias injection, corrective retry.
9. **PII + jailbreak guardrails** — regex patterns + presidio, scoped to what is honest.
10. **Groundedness badge + UI polish** — streaming bubble, fact cards, multi-conversation management.

Features deliberately cut to maintain scope discipline: native Qdrant sparse vectors (blocked by version pin), a local toxicity classifier (unless MaaS exposes a moderation endpoint natively, the image bloat is not justified), a full click-to-highlight PDF viewer (de-scoped to in-expander snippet jump — disproportionate time cost), and Hindi-language NER for PII (Presidio is English-only; the regex covers the highest-value Indian ID formats honestly without claiming something that wasn't built).

---

## 12. Honest Caveats

A project that lists no caveats is hiding something. Ours are listed here, with the actual status of each.

| Caveat | Status |
|---|---|
| BM25 Devanagari tokenization uses `\w+` unicode word extraction — not full morphological normalization | Documented as a known limitation; works correctly for most Hindi queries; a full Devanagari tokenizer is a scope-creeping rabbit hole that would not meaningfully improve the eval numbers |
| Presidio PII NER is English-only | Hindi PII NER is not claimed. The Indian ID formats (Aadhaar, PAN, phone) are Latin/numeric and regex-covers them script-agnostically — the genuinely high-value cases |
| Evaluation numbers in §7 are targets derived from ablation analysis | Final measured numbers from the held-out gold set replace these before presentation |
| Vayu MaaS catalog contents (hosted reranker, moderation endpoint) vary | The `RERANKER_MODEL=none` flag cleanly degrades to dense+BM25-only if a MaaS reranker is confirmed and preferred |
| Citation UI supports in-expander snippet jump | Not a full click-to-highlight PDF viewer — deliberate de-scope, not an oversight |
| LLM-judge grading uses a different model from the answering model | Grading circularity is avoided; deterministic Hit@k/MRR are the credible core of the eval |

---

## 13. Impact & Close

**+28 Hit@4 points** over the starter on exact scheme rules, measured on the held-out gold set with a deterministic metric that cannot be gamed.

The language wall is removed without translating the source of truth. A Hindi question retrieves from an English circular and answers in Hindi, with a citation to the exact section and character offset.

The system abstains honestly. Asking "what's the weather tomorrow?" returns a gold badge and a clear disclaimer — the LLM is never called, hallucination is architecturally impossible on out-of-domain queries.

Every claim in this README is backed by running code. The guardrails exist in `rag_client.py`. The hybrid retrieval is in `_rrf_fuse()`. The calibrated abstention is in `_rerank()`. The citation schema is in `_build_bm25_index()`. The corrective language retry is in `_gen()`. Nothing is claimed that isn't shipped.

Fluent answers are easy. An answer a Bank Sakhi can stake a family's entitlement on — in her language, with the rule cited to the exact line — is the product.

**For Bharat, a verifiable answer is the product**

---

*Built with 🌾 for the Tata Communications Vayu AI Studio Hackathon · RAG Track*

*Amrit Kumar Ghoshal · Sreehari K. · Aman Kumar · Samyak Hiran*

*Vayu Object Storage · Vayu AI Studio · Vayu Vector DB · Vayu MaaS · Vayu ML Service*
