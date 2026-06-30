# Ask-It — Starter Template

## Problem statement and outcome

**Problem:** Users often have to comb through massive documents (PDFs, policies, textbooks) in languages like Hindi, needing a quick answer they can trust. Choose a real user (e.g., a customer‑support agent, loan officer, MSME owner, junior doctor, law student, HR newcomer, student, or citizen) and a document set they care about. Build an end‑to‑end copilot **using the Vayu platform**: store the document corpus in **Vayu Object Storage**, ingest and chunk them in a **Vayu AI Studio** notebook, embed with an approved model from **Vayu Model as a Service**, index in **Vayu Vector DB (Qdrant)**, configure the RAG pipeline and register it in the **Vayu Model Registry**, and expose a chat UI via **Vayu Realtime Inference**.

**Outcome:** This starter template demonstrates the full Vayu‑centric pipeline: upload docs to **Vayu Object Storage**, ingest‑chunk‑embed‑index in **Vayu AI Studio**, store vectors in **Vayu Vector DB**, register RAG configuration in the **Vayu Model Registry**, and run a Streamlit chat app containerised and pushed to the **Vayu Hackathon Container Registry**, then served via **Vayu Realtime Inference**. The UI returns answers in plain language, cites the exact source document and line, supports multilingual queries (English + an Indian language), and respects guardrails (PII, toxicity, jailbreak).

### Chat UI preview

The final step (`05_build_app/chat_app.py`) is a Streamlit chat interface with retrieval settings, grounded answers, and expandable source citations:

![Ask-It Streamlit chat UI](./assets/ask-it/app.png)

Typical hackathon domains: customer-support manuals, HR/onboarding policies, research PDFs (add loaders if you need PDF/DOCX beyond the starter’s `.md` / `.txt` / `.html`).

**Architecture diagram:** single Excalidraw file [`diagrams/ask-it-architecture.excalidraw`](./diagrams/ask-it-architecture.excalidraw) (platform journey, ingest, query, deploy).

---

## Project layout (steps)

```text
ask-it/
├── README.md
├── requirements.txt
├── .env.example                  # Template — copy to .env and fill in values
├── 00_vayu_workspace/
│   └── README.md                 # Allocate a Vayu Workspace
│
├── 01_dataset/
│   ├── 01_dataset.ipynb          # Upload docs to Vayu Object Storage
│   └── docs/                     # Sample corpus (.md, .txt, .html)
│
├── 02_vayu_vector_databases/
│   └── README.md                 # Provision Vayu Vector DB (Qdrant)
│
├── 03_vayu_model_as_a_service/
│   └── README.md                 # Get Vayu Model as a Service key
│
├── 04_starter_kit/
│   └── qna.ipynb                 # Vayu AI Studio: chunk → MaaS embed → Vector DB index
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
| 0 | **Vayu AI Studio Workspace** | `00_vayu_workspace/` | `README.md` — create workspace (enable Docker) |
| 1 | **Vayu Object Storage** | `01_dataset/` | `01_dataset.ipynb` — sync `docs/` to object storage |
| 2 | **Vayu Vector DB** (Qdrant) | `02_vayu_vector_databases/` | `README.md` — provision DB; set `QDRANT_URL` / `QDRANT_API_KEY` |
| 3 | **Vayu Model as a Service** | `03_vayu_model_as_a_service/` | `README.md` — MaaS API key, base URL, embedding + chat models |
| 4 | **Vayu AI Studio RAG lab** | `04_starter_kit/` | `qna.ipynb` — chunk, embed (MaaS), index (Vector DB) |
| 5 | **Vayu chat app (build)** | `05_build_app/` | `chat_app.py` + `rag_client.py`; build/push Docker image |
| 6 | **Vayu ML Service (deploy)** | `06_deploy/` | Deploy image to **Vayu ML Service** — hosted Streamlit endpoint |

---

## Mapping to the Vayu “Ask-It — Guided Journey”

| Journey step | How to leverage Vayu ecosystem (detailed) |
|--------------|------------------------------------------|
| **Vayu AI Studio Workspace** | Create your workspace with **Enable Docker in the Workspace** turned on, then clone this repo ([`00_vayu_workspace/`](00_vayu_workspace/)). |
| **Vayu Object Storage** | Store raw documents (S3‑compatible). Sync `docs/` to a bucket so **Vayu AI Studio** notebooks can read them during ingest (`01_dataset.ipynb`). |
| **Vayu Vector DB** | Provision hosted **Qdrant** in AI Studio (Vector DB → Create → select **Qdrant**). Set `QDRANT_URL` and `QDRANT_API_KEY` in `ask-it/.env`. See the [Creating Qdrant guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/qdrant/#creating-qdrant). |
| **Vayu Model as a Service** | Pick embedding + chat models from the **MaaS catalog**. Set `LLM_OPENAI_API_KEY`, `EMBEDDING_OPENAI_API_KEY`, `OPENAI_BASE_URL`, `EMBEDDING_MODEL`, `CHAT_MODEL`. |
| **Vayu RAG ingest (notebook)** | `load_chunks_from_docs` → `embed_texts` (MaaS) → `upsert_chunks` into the **Vayu Vector DB** collection `COLLECTION_NAME`. |
| **Vayu RAG runtime** | `rag_client.RAGEngine` — retrieve from Vector DB, stitch context, call MaaS chat, return citations (notebook tests + Streamlit UI). |
| **Vayu chat UI** | `streamlit run chat_app.py` locally or from the Docker image; same Vector DB collection and source panel for judges. |
| **Vayu ML Service (deploy)** | Push image from Step 5, create **ML Service** in AI Studio (port **8501**, Streamlit); set Vector DB + MaaS env vars — see [`06_deploy/README.md`](06_deploy/README.md). |

---

## Tech direction / tools (Vayu ecosystem)

| Layer | Vayu / stack choice |
|--------|---------------------|
| Documents | **Vayu Object Storage** (optional) + local `01_dataset/docs/` |
| Compute | **Vayu AI Studio** — `04_starter_kit/qna.ipynb` |
| Vector search | **Vayu Vector DB** (Qdrant) |
| Embeddings + chat | **Vayu Model as a Service** — OpenAI-compatible API |
| App surface | **Streamlit** (`05_build_app/chat_app.py`) |
| Container | **`05_build_app/Dockerfile`** → registry → **`06_deploy/`** ML Service |

**In the box:** `04_starter_kit/qna.ipynb` (ingest + lab), `05_build_app/rag_client.py`, `05_build_app/chat_app.py`, `01_dataset/docs/` sample corpus, `requirements.txt`, `05_build_app/Dockerfile`.

---

## Quick start

### What this code does

1. **Vayu RAG ingest** — `04_starter_kit/qna.ipynb` chunks `01_dataset/docs/`, embeds via **Vayu Model as a Service**, upserts into **Vayu Vector DB**.
2. **Vayu RAG query** — `05_build_app/rag_client.py` embeds the question, searches Vector DB, calls **Vayu Model as a Service** chat, returns answer + citations.
3. **Vayu chat UI** — `05_build_app/chat_app.py` queries the **same** Vector DB collection; does **not** re-ingest. Run the notebook first.

### Minimal run

1. **Set up the environment**

   ```bash
   cd ask-it
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Create a `.env` file** in the project root (`ask-it/.env`) with your Vayu credentials:

   ```bash
   # Vayu Vector DB (Qdrant) — Step 2
   QDRANT_URL=<your-qdrant-url>
   QDRANT_API_KEY=<your-qdrant-api-key>
   COLLECTION_NAME=knowledge_base_rag

   # Vayu Model as a Service — Step 3
   OPENAI_BASE_URL=<your-maas-base-url>
   LLM_OPENAI_API_KEY=<your-maas-api-key>
   EMBEDDING_OPENAI_API_KEY=<your-maas-api-key>
   EMBEDDING_MODEL=<your-embedding-model>
   CHAT_MODEL=<your-chat-model>

   # Vayu Object Storage (optional) — Step 1
   VAYU_S3_KEY=<your-access-key>
   VAYU_S3_SECRET=<your-secret-key>
   VAYU_S3_ENDPOINT=<your-s3-endpoint>
   VAYU_S3_BUCKET=<your-bucket-name>
   S3_PREFIX=docs/
   ```

   Python scripts and notebooks load this file automatically via `load_dotenv`. Do not commit `.env` to git.

3. **Run ingest (once)**

   Open `04_starter_kit/qna.ipynb` in Vayu AI Studio, select the kernel, then run all cells:

   1. Open **Select Kernel** and choose **Python Environments**.

   ![Select Kernel — Python Environments](assets/kernel_select.png)

   2. Under **Select a Python Environment**, pick the **Recommended** environment (it should point to the `.venv` from [Step 0](00_vayu_workspace/)).

   ![Select a Python Environment](assets/Select_kernerl_env.png)

   See [Step 4](04_starter_kit/) for full ingest details.

4. **Launch the chat UI** (`05_build_app/`)

   ```bash
   cd 05_build_app
   streamlit run chat_app.py
   ```

   Open **http://localhost:8501** (or the Studio proxy URL, e.g. `https://<your-workspace-host>/proxy/8501`). Use the sidebar **top-k** and expand **Sources** on each reply.

   **Or build the Docker image** for [Step 6](06_deploy/) — see [`05_build_app/README.md`](05_build_app/README.md).

---

## Environment variables

| Variable | Required | Notes |
|----------|----------|--------|
| `QDRANT_URL` / `QDRANT_API_KEY` | Yes (hosted) | From **Vayu Vector DB** in AI Studio |
| `QDRANT_PATH` | Dev alternative | Local Qdrant only; omit `QDRANT_URL` |
| `LLM_OPENAI_API_KEY` / `EMBEDDING_OPENAI_API_KEY` | Yes | **Vayu Model as a Service** API keys |
| `OPENAI_BASE_URL` | Yes | **Vayu Model as a Service** base URL |
| `EMBEDDING_MODEL` / `CHAT_MODEL` | Yes | Must match models used at ingest |
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
