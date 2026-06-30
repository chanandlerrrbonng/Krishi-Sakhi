# Step 5 — Vayu chat app & Realtime Inference

**Ask-It** › **Vayu Container Registry & Realtime Inference** · `05_build_app/`

| | |
|---|---|
| **Previous** | [Step 4 — Vayu RAG ingest lab](../04_starter_kit/) |
| **Next** | [Step 6 — Deploy ML Service →](../06_deploy/) |

Build the **Ask-It** Streamlit app and Docker image locally, then continue to [Step 6 — Deploy](../06_deploy/) for the hosted **Vayu ML Service** endpoint.

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
| `Dockerfile` | Production-ready image for **Vayu Hackathon Container Registry** |

---

## Prerequisites

- [Step 4 — Vayu RAG ingest lab](../04_starter_kit/) completed — vectors in **Vayu Vector DB**
- Env vars from [Step 2 — Vayu Vector DB](../02_vayu_vector_databases/) and [Step 3 — Vayu Model as a Service](../03_vayu_model_as_a_service/)

---

## Run Locally (Dev Mode)

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

---

## Build and push Docker image

The `Dockerfile` lives in this folder, but the **build context** must be the parent **`ask-it/`** directory (one level up), because the image copies `requirements.txt` from there.

| | Path |
|---|------|
| **Build from** | `ask-it/` |
| **Dockerfile** | `ask-it/05_build_app/Dockerfile` |
| **Do not build from** | `05_build_app/` (will fail on `COPY`) |

### Vayu Container Registry

| Resource | Value |
|----------|-------|
| **Registry host** | `<YOUR_CONTAINER_REGISTRY_HOST>` |
| **Registry username** | `<YOUR_REGISTRY_USERNAME>` |
| **Registry password** | `<YOUR_REGISTRY_PASSWORD>` |

1. Log in to your hackathon / Vayu container registry:

   ```bash
   docker login <YOUR_CONTAINER_REGISTRY_HOST>
   ```

2. Build and push from the `ask-it/` root:

   ```bash
   cd ask-it

   docker build -f 05_build_app/Dockerfile -t <YOUR_CONTAINER_REGISTRY_HOST>/ask-it-chat:latest . --push
   ```

3. Note the full image reference (e.g. `<YOUR_CONTAINER_REGISTRY_HOST>/ask-it-chat:latest`) — you will enter it in the ML Service wizard in [Step 6](../06_deploy/).

| Check | |
|-------|---|
| Port in image | **8501** (Streamlit; see `EXPOSE` in Dockerfile) |
| Secrets | **Not** baked into the image — only at runtime |

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
| Docker build fails on `COPY` | Build from `ask-it/` root, not `05_build_app/` |

---

## Next: deploy to Vayu ML Service

After the image is pushed to your registry, follow **[Step 6 — Deploy](../06_deploy/README.md)** for the ML Service wizard (port **8501**, environment variables, public URL, and demo checklist).

---

## Pro Tips & Notes

- Re-running `qna.ipynb` is **required** after corpus updates!
- Never bake secrets into Docker images — use runtime environment variables instead.

---

## Navigation

| | |
|---|---|
| **Previous** | [Step 4 — Vayu RAG ingest lab](../04_starter_kit/) |
| **Next** | [Step 6 — Deploy ML Service →](../06_deploy/) |
| **🏠 Overview** | [Ask-It overview](../README.md) |
