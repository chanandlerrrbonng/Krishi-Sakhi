# Step 6 — Deploy Ask-It (Vayu ML Service)

**Ask-It** › **Vayu ML Service (Realtime Inference)** · `06_deploy/`

| | |
|---|---|
| **⬅ Previous** | [Step 5 — Build Docker image](../05_build_app/) |
| **🏁 Next** | — (journey complete) |
| **🏠 Overview** | [Ask-It overview](../README.md) |

This step takes the **Streamlit chat image** you built in [Step 5](../05_build_app/) and runs it on the **Vayu platform** as an **ML Service**. After deployment, you get a **hosted endpoint URL** in the AI Studio UI so judges and users can open Ask-It without running Streamlit locally.

---

## What you are deploying

| Piece | Where it lives |
|-------|----------------|
| Chat UI + RAG runtime | Docker image (`ask-it-chat:latest`) from [`05_build_app/Dockerfile`](../05_build_app/Dockerfile) |
| Vector search | **Vayu Vector DB** — same `QDRANT_URL` / `QDRANT_API_KEY` as [Step 2](../02_vayu_vector_databases/) |
| Embeddings + chat | **Vayu Model as a Service** — same keys/models as [Step 3](../03_vayu_model_as_a_service/) |
| Indexed corpus | **Vayu Vector DB** collection created in [Step 4](../04_starter_kit/) (`qna.ipynb`) |

The container **does not** re-ingest documents. It only queries the collection you already built. If you change `docs/`, re-run `qna.ipynb` before demoing.

---

## Prerequisites

Complete these steps first:

| Step | Folder | You need |
|------|--------|----------|
| 0 | [`00_dataset/`](../00_dataset/) | Corpus in `docs/` (optional Object Storage sync) |
| 1 | [`01_vayu_workspace/`](../01_vayu_workspace/) | Vayu AI Studio workspace |
| 2 | [`02_vayu_vector_databases/`](../02_vayu_vector_databases/) | `QDRANT_URL`, `QDRANT_API_KEY`, `COLLECTION_NAME` |
| 3 | [`03_vayu_model_as_a_service/`](../03_vayu_model_as_a_service/) | `LLM_OPENAI_API_KEY`, `EMBEDDING_OPENAI_API_KEY`, `OPENAI_BASE_URL`, `EMBEDDING_MODEL`, `CHAT_MODEL` |
| 4 | [`04_starter_kit/`](../04_starter_kit/) | `qna.ipynb` run — vectors in Vector DB |
| 5 | [`05_build_app/`](../05_build_app/) | Image built and pushed to **Vayu Hackathon Container Registry** |

**Before Step 6:** smoke-test the image locally (see [Step 5 — Dockerize](../05_build_app/README.md#dockerize-your-chatbot)) so you know RAG works with your env vars.

---

## Step 1 — Build and push the Docker image

Build context **must** be `ask-it/` (not `05_build_app/`). Full details: [`05_build_app/README.md`](../05_build_app/README.md#dockerize-your-chatbot).

```bash
cd /path/to/vayu-hackathon/ask-it

docker build -f 05_build_app/Dockerfile -t ask-it-chat:latest .
```

Tag and push to the registry your hackathon track uses (example — replace with your registry host and credentials):

```bash
# Example: tag for Vayu / hackathon registry
docker tag ask-it-chat:latest <registry-host>/ask-it-chat:latest
docker login <registry-host>
docker push <registry-host>/ask-it-chat:latest
```

Note the full image reference you pushed (e.g. `<registry-host>/ask-it-chat:latest`) — you will enter it in the ML Service wizard.

| Check | |
|-------|---|
| Image runs locally | `docker run` from Step 5 README opens **http://localhost:8501** and answers a test question |
| Port in image | **8501** (Streamlit; see `EXPOSE` in Dockerfile) |
| Secrets | **Not** baked into the image — only at runtime |

---

## Step 2 — Open Vayu ML Services

| Resource | URL |
|----------|-----|
| **ML Services list (create)** | [Create ML Service](https://ipcloud.tatacommunications.com/uat/aistudio/#/deploy/mlops-service-list) |
| **ML Service documentation** | [ML Service docs](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/ml-service/) |
| **Container registry** | [Registry docs](https://aistudio.cloudservices.tatacommunications.com/docs/aistudio/registry/) |

In AI Studio: **Deploy** → **ML Services** → **Create ML Service**.

---

## Step 3 — Create the ML Service (wizard)

Follow the platform wizard. Map Ask-It settings as below.

### 3.1 Start — image and runtime

| Field | Ask-It value |
|-------|----------------|
| **Name** | e.g. `ask-it-chat` or your team name |
| **Framework** | **Streamlit** (or **Python3** if Streamlit is not listed — app still runs via `streamlit run` in the image CMD) |
| **Private Registry → Registry URL** | Your hackathon / Vayu registry host |
| **Private Registry → Image** | Full image you pushed, e.g. `<registry-host>/ask-it-chat:latest` |
| **Private Registry → Username / Password** | Registry credentials from your track |
| **Port** | **8501** |
| **Public Expose** | Enable if you need a URL reachable outside the cluster (typical for demos) |

Optional **Args**: leave empty unless your platform team specifies extra Streamlit flags.

### 3.2 Environment variables (required)

Add each key/value pair in **Environment Variable** on the Start step (or equivalent secrets UI). Use the **same values** as in your local `ask-it/.env` and `qna.ipynb` ingest run (the `.env` file is for local dev only — it is not baked into the Docker image).

| Key | Required | Source |
|-----|----------|--------|
| `QDRANT_URL` | Yes | [Step 2](../02_vayu_vector_databases/) |
| `QDRANT_API_KEY` | Yes | [Step 2](../02_vayu_vector_databases/) |
| `LLM_OPENAI_API_KEY` | Yes | [Step 3](../03_vayu_model_as_a_service/) |
| `EMBEDDING_OPENAI_API_KEY` | Yes | [Step 3](../03_vayu_model_as_a_service/) |
| `OPENAI_BASE_URL` | Yes | [Step 3](../03_vayu_model_as_a_service/) |
| `EMBEDDING_MODEL` | Yes | Must match ingest (e.g. `Qwen/Qwen3-Embedding-8B`) |
| `CHAT_MODEL` | Yes | Must match ingest (e.g. `openai/gpt-oss-120b`) |
| `COLLECTION_NAME` | Recommended | Default `knowledge_base_rag` |

Example values (replace secrets with yours):

```text
QDRANT_URL=<VAYU_QDRANT_URL>
QDRANT_API_KEY="<VAYU_QDRANT_API_KEY>"
LLM_OPENAI_API_KEY="sk-**********************"
EMBEDDING_OPENAI_API_KEY="sk-**********************"
OPENAI_BASE_URL="<VAYU_MODEL_AS_A_SERVICE_URL>"
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
CHAT_MODEL=openai/gpt-oss-120b
COLLECTION_NAME="<COLLECTION_NAME>"
```

Do **not** set `QDRANT_PATH` for hosted deployment unless you intentionally use on-disk Qdrant inside the container (not recommended for this template).

### 3.3 Infrastructure

Select the **Datacenter**, **Business Unit**, and **Environment** assigned to your hackathon workspace (same as other Vayu resources).

### 3.4 Configure compute

| Field | Guidance |
|-------|----------|
| **Resources / flavor** | CPU is enough for Streamlit + API calls; add GPU only if your track requires it |
| **Replicas** | `1` for demo; increase for load testing |

### 3.5 Observability

Enable **Monitoring** and **Logging** if available — useful when debugging retrieval or MaaS errors during the demo.

### 3.6 Review and submit

Review name, image, port **8501**, and all environment variables. Click **Submit** and wait until status is **ready** (or equivalent) on the ML Services list.

---

## Step 4 — Get the endpoint and verify

1. Open **ML Services List** → click your service **Name**.
2. On **View ML Service**, check **Summary** and **Connect** for the public or internal URL.
3. Open the URL in a browser. You should see the Ask-It Streamlit UI (same as local, see [overview screenshot](../README.md#chat-ui-preview)).
4. Ask a question that exists in your indexed docs (e.g. field-trip reminder from `text-example.txt`).
5. Expand **Sources** on the reply — citations should match [Step 4](../04_starter_kit/) ingest.

| Symptom | What to check |
|---------|----------------|
| Page does not load | Port **8501**, **Public Expose**, pod status **ready** |
| “Failed to initialize RAG Engine” | Env vars in ML Service match Step 2–3; no typos in keys |
| Empty or wrong answers | Re-run `qna.ipynb`; `COLLECTION_NAME` and `EMBEDDING_MODEL` match ingest |
| Model errors | `CHAT_MODEL` / `OPENAI_BASE_URL`; API key valid and credited |

---

## Step 5 — Optional: Model Registry

If your hackathon track requires registering the RAG configuration:

| Resource | URL |
|----------|-----|
| **Model Registry** | [Model Registry list](https://ipcloud.tatacommunications.com/uat/aistudio/#/deploy/model-registry-list) |

Register metadata such as collection name, embedding model, chat model, and top-k — aligned with [`rag_client.py`](../05_build_app/rag_client.py). Deployment still runs through **ML Service** using the Docker image from Step 5.

---

## Environment variable reference

Same table as the [Ask-It overview](../README.md#docker); required at **runtime** on the ML Service, not in the Dockerfile.

| Variable | Required | Notes |
|----------|----------|--------|
| `QDRANT_URL` / `QDRANT_API_KEY` | Yes (hosted) | From **Vayu Vector DB** |
| `QDRANT_PATH` | No | Local dev only — omit in ML Service |
| `LLM_OPENAI_API_KEY` / `OPENAI_BASE_URL` | Yes | **Vayu Model as a Service** |
| `OPENAI_BASE_URL` | Yes | **Vayu Model as a Service** |
| `EMBEDDING_OPENAI_API_KEY` | Yes | **Vayu Model as a Service** |
| `EMBEDDING_MODEL` / `CHAT_MODEL` | Yes | Must match `qna.ipynb` ingest |
| `COLLECTION_NAME` | No | Default `knowledge_base_rag` |

---

## Demo checklist (submission-ready)

- [ ] Corpus indexed in Vector DB ([`04_starter_kit/qna.ipynb`](../04_starter_kit/qna.ipynb))
- [ ] Docker image built from `ask-it/` and pushed to registry
- [ ] ML Service **ready** with port **8501** and all env vars set
- [ ] Public/demo URL opens Ask-It UI
- [ ] Test question returns a grounded answer with **Sources** expanded
- [ ] Endpoint URL documented for judges (README or slide)

---

## Pro tips

- **Re-deploy after env changes** — Editing env vars in the ML Service usually requires a restart or new revision; confirm in the UI after saving.
- **Same models end-to-end** — Changing `EMBEDDING_MODEL` without re-ingesting breaks vector search.
- **Credits** — Hosted chat calls MaaS on every question; use a smaller chat model for dry runs ([Step 3](../03_vayu_model_as_a_service/)).
- **Never commit secrets** — Registry passwords and API keys only in the platform UI or secure env stores.

---

## Jump around

| | |
|---|---|
| **⬅ Previous** | [Step 5 — Build app & Docker image](../05_build_app/) |
| **Step 4** | [Vayu RAG ingest lab](../04_starter_kit/) |
| **🏠 Overview** | [Ask-It overview](../README.md) |
