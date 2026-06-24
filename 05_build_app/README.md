# Step 5 — Vayu chat app & Realtime Inference

**Ask-It** › **Vayu Container Registry & Realtime Inference** · `05_build_app/`

Build the **Ask-It** Streamlit app and Docker image locally, then continue to [Step 6 — Deploy](../06_deploy/) for the hosted **Vayu ML Service** endpoint.

---

## Quick Navigation

|        |        |
|--------|--------|
| **⬅ Previous** | [Step 4 — Vayu RAG ingest lab](../04_starter_kit/) |
| **Next ➡**    | [Step 6 — Deploy ML Service](../06_deploy/) |

---

## What’s In This Step?

- **Streamlit** chat UI for Vayu RAG (questions + source citations)
- **`Dockerfile`** — image for **Vayu Hackathon Container Registry** and **Vayu Realtime Inference**

---

## Prerequisites

- ✅ [Step 4 — Vayu RAG ingest lab](../04_starter_kit/) completed — vectors in **Vayu Vector DB**
- ✅ Env vars from [Step 2 — Vayu Vector DB](../02_vayu_vector_databases/) and [Step 3 — Vayu Model as a Service](../03_vayu_model_as_a_service/)

---

## Folder Contents

| File           | Description                               |
|----------------|-------------------------------------------|
| `chat_app.py`  | Streamlit interface for asking questions  |
| `rag_client.py`| Abstraction for retrieval & LLM chat      |
| `Dockerfile`   | Production-ready image setup              |

---

## Run Locally (Dev Mode)

```bash
# Set up a Python 3.12 virtual environment
pip install virtualenv

virtualenv venv
source venv/bin/activate

cd ask-it
pip install -r requirements.txt

cd 05_build_app

export QDRANT_URL="<VAYU_QDRANT_URL>"
export QDRANT_API_KEY="<VAYU_QDRANT_API_KEY>"
export LLM_OPENAI_API_KEY="sk-**********************"
export EMBEDDING_OPENAI_API_KEY="sk-**********************"
export OPENAI_BASE_URL="<VAYU_MODEL_AS_A_SERVICE_URL>"
export EMBEDDING_MODEL="Qwen/Qwen3-Embedding-8B"
export CHAT_MODEL="openai/gpt-oss-120b"
export COLLECTION_NAME="<COLLECTION_NAME>"

streamlit run chat_app.py
```

- Open your browser at **http://localhost:8501**
- Change **Top-K** from the sidebar to fine-tune answers
- Click and expand **Sources** for each response

---

## Deploy your app using Vayu ML Services

<Insert it Vayu Container Registry Steps and docs>

The `Dockerfile` lives in this folder, but the **build context** must be the parent **`ask-it/`** directory (one level up), because the image copies `requirements.txt` from there.

| | Path |
|---|------|
| **Build from** | `ask-it/` |
| **Dockerfile** | `ask-it/05_build_app/Dockerfile` |
| **Do not build from** | `05_build_app/` (will fail on `COPY`) |

```bash
# 1. Go to ask-it/ (parent of this folder)
cd /path/to/vayu-hackathon/ask-it

# 2. Build — note -f points at this Dockerfile, . is ask-it/
docker build -f 05_build_app/Dockerfile -t <VAYU_CONTAINER_REGISTRY>/ask-it-chat:latest . --push
```
---

## Next: deploy to Vayu ML Service

After the image is pushed to your registry, follow **[Step 6 — Deploy](../06_deploy/README.md)** for the ML Service wizard (port **8501**, environment variables, public URL, and demo checklist).

---

## Pro Tips & Notes

- Re-running `qna.ipynb` is **required** after corpus updates!
- Never bake secrets into Docker images—use runtime environment variables instead.

---

## Jump Around

|        |        |
|--------|--------|
| **⬅ Previous** | [Step 4 — Vayu RAG ingest lab](../04_starter_kit/) |
| **🏠 Overview**| [Ask-It overview](../README.md)        |

---
