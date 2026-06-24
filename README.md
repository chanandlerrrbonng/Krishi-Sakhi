# Ask-It — Starter Template

## Problem statement and outcome

**Problem:** Users often have to comb through massive documents (PDFs, policies, textbooks) in languages like Hindi, needing a quick answer they can trust. Choose a real user (e.g., a customer‑support agent, loan officer, MSME owner, junior doctor, law student, HR newcomer, student, or citizen) and a document set they care about. Build an end‑to‑end copilot **using the Vayu platform**: store the document corpus in **Vayu Object Storage**, ingest and chunk them in a **Vayu AI Studio** notebook, embed with an approved model from **Vayu Model as a Service**, index in **Vayu Vector DB (Qdrant)**, configure the RAG pipeline and register it in the **Vayu Model Registry**, and expose a chat UI via **Vayu Realtime Inference**.

**Outcome:** This starter template demonstrates the full Vayu‑centric pipeline: upload docs to **Vayu Object Storage**, ingest‑chunk‑embed‑index in **Vayu AI Studio**, store vectors in **Vayu Vector DB**, register RAG configuration in the **Vayu Model Registry**, and run a Streamlit chat app containerised and pushed to the **Vayu Hackathon Container Registry**, then served via **Vayu Realtime Inference**. The UI returns answers in plain language, cites the exact source document and line, supports multilingual queries (English + an Indian language), and respects guardrails (PII, toxicity, jailbreak).

### Chat UI preview

The final step (`05_build_app/chat_app.py`) is a Streamlit chat interface with retrieval settings, grounded answers, and expandable source citations:

![Ask-It Streamlit chat UI](../assets/ask-it/app.png)

Typical hackathon domains: customer-support manuals, HR/onboarding policies, research PDFs (add loaders if you need PDF/DOCX beyond the starter’s `.md` / `.txt` / `.html`).

---

## Project layout (steps)

```
ask-it/
├── README.md
├── requirements.txt
│
├── 00_dataset/
│   ├── 00_dataset.ipynb          # Upload docs to Vayu Object Storage
│   └── docs/                     # Sample corpus (.md, .txt, .html)
│
├── 01_vayu_workspace/
│   └── README.md                 # Allocate a Vayu Workspace
│
├── 02_vayu_vector_databases/
│   └── README.md                 # Provision Vayu Vector DB (Qdrant)
│
├── 03_vayu_model_as_a_service/
│   └── README.md                 # Get Vayu Model as a Service key
│
├── 04_starter_kit/
│   └── qna.ipynb                 # Vayu AI Studio: chunk → Vayu Model as a Service embed → Vector DB index
│
├── 05_build_app/
│   ├── chat_app.py               # Streamlit chat UI
│   ├── rag_client.py             # RAG engine (retrieve + prompt + citations)
│   ├── Dockerfile                # Build image for registry
│   └── README.md                 # Local run + Docker build
│
└── 06_deploy/
    └── README.md                 # Push image + Vayu ML Service endpoint
```

| Step | Vayu service | Folder | What to run / open |
|------|--------------|--------|-------------------|
| 0 | **Vayu Object Storage** | `00_dataset/` | `00_dataset.ipynb` — sync `docs/` to object storage |
| 1 | **Vayu AI Studio Workspace** | `01_vayu_workspace/` | `README.md` — create workspace, install deps |
| 2 | **Vayu Vector DB** (Qdrant) | `02_vayu_vector_databases/` | `README.md` — provision DB; set `QDRANT_URL` / `QDRANT_API_KEY` |
| 3 | **Vayu Model as a Service** | `03_vayu_model_as_a_service/` | `README.md` — Vayu Model as a Service API key, base URL, embedding + chat models |
| 4 | **Vayu AI Studio RAG lab** | `04_starter_kit/` | `qna.ipynb` — chunk, embed (Vayu Model as a Service), index (Vector DB) |
| 5 | **Vayu chat app (build)** | `05_build_app/` | `chat_app.py` + `rag_client.py`; build/push Docker image |
| 6 | **Vayu ML Service (deploy)** | `06_deploy/` | Deploy image to **Vayu ML Service** — hosted Streamlit endpoint |

---

## Mapping to the Vayu “Ask-It — Guided Journey”

This table ties each step of the Vayu platform to the concrete artifacts in this repository, helping you see where code lives and which Vayu services you need to provision.

| Journey step | How to leverage Vayu ecosystem (detailed) |
|--------------|------------------------------------------|
| **Vayu Object Storage** | Store raw documents (S3‑compatible). Sync `docs/` to a bucket so **Vayu AI Studio** notebooks can read them during ingest (`00_dataset.ipynb`). |
| **Vayu AI Studio Workspace** | Open `qna.ipynb` in **Vayu AI Studio** (or local Jupyter). Use a Python 3.12 venv, `cd ask-it`, `pip install -r requirements.txt`. |
| **Vayu Vector DB** | Provision hosted **Qdrant** in AI Studio (Vector DB → Create). Export `QDRANT_URL` and `QDRANT_API_KEY` for the notebook and Streamlit app. |
| **Vayu Model as a Service** | Pick embedding + chat models from the **Vayu Model as a Service catalog**. Set `LLM_OPENAI_API_KEY`, `EMBEDDING_OPENAI_API_KEY`, `OPENAI_BASE_URL`, `EMBEDDING_MODEL`, `CHAT_MODEL`. |
| **Vayu RAG ingest (notebook)** | `load_chunks_from_docs` → `embed_texts` (Vayu Model as a Service) → `upsert_chunks` into the **Vayu Vector DB** collection `COLLECTION_NAME`. |
| **Vayu RAG runtime** | `rag_client.RAGEngine` — retrieve from Vector DB, stitch context, call Vayu Model as a Service chat, return citations (notebook tests + Streamlit UI). |
| **Vayu chat UI** | `streamlit run chat_app.py` locally or from the Docker image; same Vector DB collection and source panel for judges. |
| **Vayu ML Service (deploy)** | Push image from Step 5, create **ML Service** in AI Studio (port **8501**, Streamlit); set Vector DB + MaaS env vars — see [`06_deploy/README.md`](06_deploy/README.md). |


---

## Tech direction / tools (Vayu ecosystem)

| Layer | Vayu / stack choice |
|--------|---------------------|
| Documents | **Vayu Object Storage** (optional) + local `00_dataset/docs/` |
| Compute | **Vayu AI Studio** — `04_starter_kit/qna.ipynb` |
| Vector search | **Vayu Vector DB** (Qdrant) |
| Embeddings + chat | **Vayu Model as a Service** — OpenAI-compatible API |
| App surface | **Streamlit** (`05_build_app/chat_app.py`) |
| Container | **`05_build_app/Dockerfile`** → registry → **`06_deploy/`** ML Service |

**In the box:** `04_starter_kit/qna.ipynb` (ingest + lab), `05_build_app/rag_client.py`, `05_build_app/chat_app.py`, `00_dataset/docs/` sample corpus, `requirements.txt`, `05_build_app/Dockerfile`.

---

## Quick start

### What this code does

1. **Vayu RAG ingest** — `04_starter_kit/qna.ipynb` chunks `00_dataset/docs/`, embeds via **Vayu Model as a Service**, upserts into **Vayu Vector DB**.
2. **Vayu RAG query** — `05_build_app/rag_client.py` embeds the question, searches Vector DB, calls **Vayu Model as a Service** chat, returns answer + citations.
3. **Vayu chat UI** — `05_build_app/chat_app.py` queries the **same** Vector DB collection; does **not** re-ingest. Run the notebook first.

### Minimal run

Set up the environment **once** (step 2 below assumes this venv stays active):

```bash
# Set up a Python 3.12 virtual environment
pip install virtualenv
virtualenv env
source env/bin/activate

cd ask-it
pip install -r requirements.txt

export QDRANT_URL="<VAYU_QDRANT_URL>"
export QDRANT_API_KEY="<VAYU_QDRANT_API_KEY>"
export LLM_OPENAI_API_KEY="sk-**********************"
export EMBEDDING_OPENAI_API_KEY="sk-**********************"
export OPENAI_BASE_URL="<VAYU_MODEL_AS_A_SERVICE_URL>"
export EMBEDDING_MODEL="Qwen/Qwen3-Embedding-8B"
export CHAT_MODEL="openai/gpt-oss-120b"
export COLLECTION_NAME="<COLLECTION_NAME>"
```

1. Run all cells in **`04_starter_kit/qna.ipynb`** in **Vayu AI Studio** (or local Jupyter).
2. Start the UI:

```bash
cd 05_build_app
streamlit run chat_app.py
```

Open **http://localhost:8501** (or the Studio proxy URL). Use the sidebar **top-k** and expand **Sources** on each reply.

### Docker

**Build context must be `ask-it/`** (the folder that contains `requirements.txt` and `05_build_app/`). Do **not** run `docker build` from inside `05_build_app/` — paths like `COPY ../requirements.txt` will fail.

```bash
# From your clone (adjust if your repo path differs)
cd vayu-hackathon/ask-it

docker build -f 05_build_app/Dockerfile -t <VAYU_CONTAINER_REGISTRY>/ask-it-chat:latest . --push
```

Push the image to your registry, then deploy on **Vayu ML Service** — full steps: [`06_deploy/README.md`](06_deploy/README.md). Build details: [`05_build_app/README.md`](05_build_app/README.md).

| Variable | Required | Notes |
|----------|----------|--------|
| `QDRANT_URL` / `QDRANT_API_KEY` | Yes (hosted) | From **Vayu Vector DB** in AI Studio |
| `QDRANT_PATH` | Dev alternative | Local Qdrant only; omit `QDRANT_URL` |
| `LLM_OPENAI_API_KEY` / `OPENAI_BASE_URL` | Yes | **Vayu Model as a Service** credentials and base URL |
| `OPENAI_BASE_URL` | Yes | **Vayu Model as a Service** credentials and base URL |
| `EMBEDDING_OPENAI_API_KEY` | Yes | **Vayu Model as a Service** credentials and base URL |
| `EMBEDDING_MODEL` / `CHAT_MODEL` | Yes | Must match models used at ingest |
| `CHAT_MODEL` | Yes | Must match models used at ingest |
| `COLLECTION_NAME` | No | Default `knowledge_base_rag` |

---

## Tips

- **Ingest before you chat** — The Streamlit app only queries; judges should see a fresh index from your real domain files.
- **Show sources** — Expand citations in the UI; grounded answers score better than fluent hallucinations.
- **Embedding dimension** — If you change embedding models, recreate the **Vayu Vector DB** collection (vector size must match).
- **Credits** — Use smaller chat models for dry runs; watch usage in Vayu observability during the demo.
- **PDF/DOCX** — Add `pypdf` / `python-docx` loaders in the notebook if your problem needs them.

---

## License

Use and modify for the **Vayu Hackathon** submission unless your team repo specifies otherwise.
