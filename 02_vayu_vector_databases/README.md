# Step 2 — Vayu Vector DB (Qdrant)

**Ask-It** › **Vayu Vector DB** · `02_vayu_vector_databases/`

| | |
|---|---|
| **Previous** | [← Step 1 — Vayu Object Storage](../01_dataset/) |
| **Next** | [Step 3 — Vayu Model as a Service →](../03_vayu_model_as_a_service/) |

Set up the **Vayu Vector DB (Qdrant)** for Retrieval-Augmented Generation (RAG).

---

## Open Vector DB

Go to [Vayu Vector DB](https://ipcloud.tatacommunications.com/aistudio/#/experiment/vectordatabase-list).

---

## Quick Start

1. **Provision Vayu Vector DB (Qdrant):** In AI Studio, click **Create Vector Database** and select the **Qdrant** engine under **Vector Type** (see the [Creating Qdrant Vector DB guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/qdrant/#creating-qdrant)).
2. **Wait for Ready:** Submit the deployment and wait until the status shows **Ready**.
3. **Collect access details:** Note your **`QDRANT_URL`** and **`QDRANT_API_KEY`** from the console. When you copy the URL, paste the link as-is but remove the trailing `dashboard` at the end (e.g. use `https://<your-host>` instead of `https://<your-host>/dashboard`).
4. **Set environment variables:** Copy `.env.example` to `.env` at the **ask-it** repo root and fill in your values (used by notebooks and `chat_app.py`):

   ```bash
   cd ask-it
   cp .env.example .env
   # Edit .env — set QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME
   ```

5. **Local development (optional):** For local testing, use on-disk Qdrant with the `QDRANT_PATH` variable in your notebook, instead of the hosted service.

---

## Resources

| Resource | URL |
|----------|-----|
| Provision Vayu Vector DB | https://ipcloud.tatacommunications.com/aistudio/#/experiment/vectordatabase-list |
| Docs (Milvus) | https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/milvus |
| Docs (Qdrant) | https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/qdrant |

---

## Navigation

| | |
|---|---|
| **Previous** | [← Step 1 — Vayu Object Storage](../01_dataset/) |
| **Next** | [Step 3 — Vayu Model as a Service →](../03_vayu_model_as_a_service/) |
| **Overview** | [Ask-It overview](../README.md) |
