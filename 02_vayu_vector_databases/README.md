# Step 2 — Vayu Vector DB (Qdrant)

**Ask-It** › **Vayu Vector DB** · `02_vayu_vector_databases/`

|              |                                                                 |
|--------------|-----------------------------------------------------------------|
| **Previous** | [← Step 1 — Vayu AI Studio Workspace](../01_vayu_workspace/)    |
| **Next**     | [Step 3 — Vayu Model as a Service →](../03_vayu_model_as_a_service/) |

Set up the **Vayu Vector DB (Qdrant)** for Retrieval-Augmented Generation (RAG).

---

## Quick Start

1. **Provision Vayu Vector DB:**  
   In Vayu AI Studio, create a new Vector DB (Qdrant) instance.
2. **Collect Access Details:**  
   After provisioning, note your **`QDRANT_URL`** and **`QDRANT_API_KEY`** from the console.
3. **Set environment variables:**  
   Copy `.env.example` to `.env` at the **ask-it** repo root and fill in your values (used by notebooks and `chat_app.py`):

   ```bash
   cd ask-it
   cp .env.example .env
   # Edit .env — set QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME
   ```
4. **Local Development (Optional):**  
   For local testing, use on-disk Qdrant with the `QDRANT_PATH` variable in your notebook, instead of the hosted service.

---

## Resources

| Resource               | URL                                                                                       |
|------------------------|-------------------------------------------------------------------------------------------|
| Provision Vayu Vector DB | https://ipcloud.tatacommunications.com/aistudio/#/experiment/vectordatabase-list    |
| Docs (Milvus)          | https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/milvus|
| Docs (Qdrant)          | https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/qdrant|

---

## Navigation

|              |                                                                 |
|--------------|-----------------------------------------------------------------|
| **Previous** | [← Step 1 — Vayu AI Studio Workspace](../01_vayu_workspace/)    |
| **Next**     | [Step 3 — Vayu Model as a Service →](../03_vayu_model_as_a_service/) |
| **Overview** | [Ask-It overview](../README.md)                                 |
