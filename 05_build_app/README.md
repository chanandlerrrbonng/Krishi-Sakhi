# Step 5 — Vayu chat app & Realtime Inference

**Ask-It** › **Streamlit Chat App** · `05_build_app/`

| | |
|---|---|
| **Previous** | [Step 4 — Vayu RAG ingest lab](../04_starter_kit/) |
| **Next** | [Step 6 — Deploy ML Service →](../06_deploy/) |

Run the **Ask-It** Streamlit chat app locally, then continue to [Step 6 — Deploy](../06_deploy/) to build, sign, and push the Docker image as a **Vayu ML Service**.

---

## Pipeline flow

```text
User question (chat_app.py)
        │
        ▼
Embed query (rag_client.py → Vayu Model as a Service)
        │
        ▼
Vector search (Vayu Vector DB — collection from Step 4)
        │
        ▼
LLM answer + citations (Vayu Model as a Service chat)
        │
        ▼
Streamlit UI (port 8501)
```

---

## What's In This Step?

| File | Description |
|------|-------------|
| `chat_app.py` | Streamlit interface for asking questions |
| `rag_client.py` | Abstraction for retrieval & LLM chat |
| `Dockerfile` | Used in [Step 6](../06_deploy/) to build the ML Service image |

---

## Prerequisites

- [Step 4 — Vayu RAG ingest lab](../04_starter_kit/) completed — vectors in **Vayu Vector DB**
- Env vars from [Step 2 — Vayu Vector DB](../02_vayu_vector_databases/) and [Step 3 — Vayu Model as a Service](../03_vayu_model_as_a_service/)

---

## Run locally

```bash
cd ask-it
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your Vayu Vector DB and Model as a Service credentials

cd 05_build_app
streamlit run chat_app.py
```

- Open your browser at **http://localhost:8501**
- When running inside a **Vayu AI Studio workspace**, use the workspace proxy URL instead (e.g. `https://<your-workspace-host>/proxy/8501`)
- Change **Top-K** from the sidebar to fine-tune answers
- Click and expand **Sources** for each response

When local testing works, continue to [Step 6 — Deploy](../06_deploy/) to build, sign, and push the Docker image.

---

## Environment variables

| Variable | Required | Used by | Purpose |
|----------|----------|---------|---------|
| `QDRANT_URL` | Yes | `rag_client.py` | Vayu Vector DB endpoint |
| `QDRANT_API_KEY` | Yes | `rag_client.py` | Vector DB auth |
| `LLM_OPENAI_API_KEY` | Yes | `rag_client.py` | MaaS chat API key |
| `EMBEDDING_OPENAI_API_KEY` | Yes | `rag_client.py` | MaaS embedding API key |
| `OPENAI_BASE_URL` | Yes | `rag_client.py` | MaaS base URL |
| `EMBEDDING_MODEL` | Yes | `rag_client.py` | Must match ingest |
| `CHAT_MODEL` | Yes | `rag_client.py` | Must match ingest |
| `COLLECTION_NAME` | No | `rag_client.py` | Default `knowledge_base_rag` |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| **Failed to initialize RAG Engine** | Check `.env` values; confirm Vector DB and MaaS credentials |
| Empty or wrong answers | Re-run `qna.ipynb`; verify `COLLECTION_NAME` and `EMBEDDING_MODEL` match ingest |
| Model errors | Confirm `CHAT_MODEL` / `OPENAI_BASE_URL`; check API key and credits |
| Page won't load in workspace | Use the proxy URL (`/proxy/8501`) instead of `localhost` |

---

## Pro tips

- Re-running `qna.ipynb` is **required** after corpus updates!
- Never bake secrets into Docker images — use runtime environment variables in the ML Service (Step 6).

---

## Navigation

| | |
|---|---|
| **Previous** | [Step 4 — Vayu RAG ingest lab](../04_starter_kit/) |
| **Next** | [Step 6 — Deploy ML Service →](../06_deploy/) |
| **🏠 Overview** | [Ask-It overview](../README.md) |
