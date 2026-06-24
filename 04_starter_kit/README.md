# Step 4 — Vayu RAG ingest lab (AI Studio)

**Ask-It** › **Vayu AI Studio RAG lab** · `04_starter_kit/`

|        |                             |
|--------|-----------------------------|
| **⬅ Previous** | [Step 3 — Vayu Model as a Service](../03_vayu_model_as_a_service/) |
| **Next ➡**     | [Step 5 — Vayu chat app](../05_build_app/) |

**Before using the Vayu chat UI, run `qna.ipynb` in Vayu AI Studio.**  
This notebook chunks your documents, embeds them via **Vayu Model as a Service**, and indexes them in **Vayu Vector DB (Qdrant)**.

---

## Prerequisites

Make sure you've completed steps **0** to **3**:

| Step | Vayu service / folder |
|------|------------------------|
| 0    | [Vayu Object Storage](../00_dataset/) — files in `docs/` |
| 1    | [Vayu AI Studio Workspace](../01_vayu_workspace/) |
| 2    | [Vayu Vector DB](../02_vayu_vector_databases/) — `QDRANT_URL`, `QDRANT_API_KEY` |
| 3    | [Vayu Model as a Service](../03_vayu_model_as_a_service/) — API key, base URL, model IDs |

Install dependencies:

![Setting up](../../assets/install.png)

```bash
# Set up a Python 3.12 virtual environment
pip install virtualenv

virtualenv venv
source venv/bin/activate

cd ask-it
pip install -r requirements.txt
```

---

## What does `qna.ipynb` do?

| Stage   | Description                                                                          |
|---------|--------------------------------------------------------------------------------------|
| Connect | Sets up **Vayu Vector DB** (Qdrant) and **Vayu Model as a Service** clients                        |
| Probe   | Checks embedding dimensions to auto-configure the collection                         |
| Index   | Chunks documents in `DOCS_DIR`, generates embeddings, and upserts to `COLLECTION_NAME` |
| Test    | Runs `rag_answer()` to perform RAG with citations                                    |

Set which documents to use:

```python
DOCS_DIR = Path("../00_dataset/docs")
```

**Tips:**
- Using hosted **Vayu Vector DB**? Switch to `hosted_instance()` in the notebook (`local_db()` is for local Qdrant only).
- Need to rebuild? Call `ensure_collection(qdrant, recreate=True)` *before* running `upsert_chunks`.

---

## Key functions

| Function                  | Purpose                             |
|---------------------------|-------------------------------------|
| `load_chunks_from_docs`   | Read files and split into chunks    |
| `embed_texts`             | Embeddings via Vayu Model as a Service            |
| `upsert_chunks`           | Upsert vectors to Vayu Vector DB    |
| `retrieve` & `rag_answer` | Query + generate answer with sources|

---

## What happens after ingest?

With the venv still active from **Install dependencies** above (and env vars from Steps 2–3):

```bash
cd 05_build_app
streamlit run chat_app.py
```

Use the same environment variables as in **Step 2 (Vayu Vector DB)** and **Step 3 (Vayu Model as a Service)**.

---

## Pro tips

- Use the same embedding and chat models as [Step 3 — Vayu Model as a Service](../03_vayu_model_as_a_service/).
- If you change embedding models, **recreate** the Vayu Vector DB collection (vector size must match).

---

## Navigation

|        |                             |
|--------|-----------------------------|
| **⬅ Previous** | [Step 3 — Vayu Model as a Service](../03_vayu_model_as_a_service/) |
| **Next ➡**     | [Step 5 — Vayu chat app](../05_build_app/) |
| **🏠 Overview**| [Ask-It overview](../README.md)                  |
