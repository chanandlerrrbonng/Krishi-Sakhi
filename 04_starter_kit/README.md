# Step 4 — Vayu RAG ingest lab (AI Studio)

**Ask-It** › **Vayu AI Studio RAG lab** · `04_starter_kit/`

| | |
|---|---|
| **⬅ Previous** | [Step 3 — Vayu Model as a Service](../03_vayu_model_as_a_service/) |
| **Next ➡** | [Step 5 — Vayu chat app](../05_build_app/) |

**Before using the Vayu chat UI, run `qna.ipynb` in Vayu AI Studio.**  
This notebook chunks your documents, embeds them via **Vayu Model as a Service**, and indexes them in **Vayu Vector DB (Qdrant)**.

---

## Folder Contents

| File | Description |
|------|-------------|
| `qna.ipynb` | Chunk documents, embed via MaaS, upsert to Vector DB, test RAG with citations |

---

## Prerequisites

| Step | Vayu service / folder |
|------|------------------------|
| 0 | [Vayu AI Studio Workspace](../00_vayu_workspace/) |
| 1 | [Vayu Object Storage](../01_dataset/) — files in `docs/` |
| 2 | [Vayu Vector DB](../02_vayu_vector_databases/) — `QDRANT_URL`, `QDRANT_API_KEY` |
| 3 | [Vayu Model as a Service](../03_vayu_model_as_a_service/) — API key, base URL, model IDs |

Install dependencies:

![Setting up](../assets/install.png)

```bash
cd ask-it
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with credentials from Steps 2–3
```

**Required environment variables** (set in `ask-it/.env` — the config cell fails fast if any are missing):

```bash
# QDRANT_URL, QDRANT_API_KEY, LLM_OPENAI_API_KEY,
# EMBEDDING_OPENAI_API_KEY, OPENAI_BASE_URL, COLLECTION_NAME, etc.
```

---

## Quick Start

1. **Open the ingest notebook:** `04_starter_kit/qna.ipynb` in your Vayu AI Studio workspace, then select the kernel:

   1. Open **Select Kernel** and choose **Python Environments**.

   ![Select Kernel — Python Environments](../assets/kernel_select.png)

   2. Under **Select a Python Environment**, pick the **Recommended** environment (it should point to the `.venv` from [Step 0](../00_vayu_workspace/)).

   ![Select a Python Environment](../assets/Select_kernerl_env.png)

2. **Run all cells:** The notebook chunks documents, embeds them, upserts to Vector DB, and tests `rag_answer()` with citations.

3. **Continue to the chat app:** Proceed to [Step 5](../05_build_app/) to run the Streamlit UI locally, then [Step 6](../06_deploy/) to deploy.

---

## What does `qna.ipynb` do?

| Stage | Description |
|-------|-------------|
| Connect | Sets up **Vayu Vector DB** (Qdrant) and **Vayu Model as a Service** clients |
| Probe | Checks embedding dimensions to auto-configure the collection |
| Index | Chunks documents in `DOCS_DIR`, generates embeddings, and upserts to `COLLECTION_NAME` |
| Test | Runs `rag_answer()` to perform RAG with citations |

Set which documents to use:

```python
DOCS_DIR = Path("../01_dataset/docs")
```

**Tips:**
- Using hosted **Vayu Vector DB**? In **cell 6** of `qna.ipynb`, comment out `qdrant = local_db()` and uncomment `qdrant = hosted_instance()` (`local_db()` is for on-disk Qdrant only).
- Need to rebuild the index? In the same **cell 6**, uncomment `ensure_collection(qdrant, recreate=True)` before running **cell 7** (`upsert_chunks(chunks)`). Cell 7’s header comment also notes this.

---

## Key functions

| Function | Purpose |
|----------|---------|
| `load_chunks_from_docs` | Read files and split into chunks |
| `embed_texts` | Embeddings via Vayu Model as a Service |
| `upsert_chunks` | Upsert vectors to Vayu Vector DB |
| `retrieve` & `rag_answer` | Query + generate answer with sources |

---

## What happens after ingest?

With the venv still active from **Install dependencies** above (and env vars from Steps 2–3):

```bash
cd 05_build_app
streamlit run chat_app.py
```

Use the same `.env` values as in **Step 2 (Vayu Vector DB)** and **Step 3 (Vayu Model as a Service)**.

---

## Pro tips

- Use the same embedding and chat models as [Step 3 — Vayu Model as a Service](../03_vayu_model_as_a_service/).
- If you change embedding models, **recreate** the Vayu Vector DB collection (vector size must match).

---

## Navigation

| | |
|---|---|
| **⬅ Previous** | [Step 3 — Vayu Model as a Service](../03_vayu_model_as_a_service/) |
| **Next ➡** | [Step 5 — Vayu chat app](../05_build_app/) |
| **🏠 Overview** | [Ask-It overview](../README.md) |
