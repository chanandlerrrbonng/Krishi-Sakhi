# Step 3 — Vayu Model as a Service

**Ask-It** › **Vayu Model as a Service** · `03_vayu_model_as_a_service/`

| | |
|---|---|
| **Previous** | [← Step 2 — Vayu Vector DB](../02_vayu_vector_databases/) |
| **Next** | [Step 4 — Vayu RAG ingest lab →](../04_starter_kit/) |

Set up **Vayu Model as a Service** for both text embeddings and chat completion.

---

## Open Model Catalog

Go to the [Vayu Model as a Service catalog](https://ai-gateway.cloudservices.tatacommunications.com/models/models/home).

For detailed setup instructions, see the **Vayu Model as a Service** documentation in AI Studio (link from your tenant console).

---

## Quick Setup

1. **Pick your models**
   - Choose an **embedding model** (for converting text to vectors).
   - Choose a **chat model** (for conversational/answering capabilities).

2. **Get API credentials**
   - Copy your API key and the base endpoint URL from the catalog or your Workspace details.

3. **Configure `.env`**

   At the **ask-it** repo root, copy `.env.example` to `.env` and set these variables (used by `qna.ipynb` and `05_build_app/`):

   ```bash
   cd ask-it
   cp .env.example .env
   # Edit .env — OPENAI_BASE_URL, CHAT_MODEL, LLM_OPENAI_API_KEY,
   # EMBEDDING_MODEL, EMBEDDING_OPENAI_API_KEY
   ```

4. **Continue**

   Go to [Step 4 — Vayu RAG ingest lab →](../04_starter_kit/) and run `qna.ipynb` in Vayu AI Studio.

---

## Key Points

- The **embedding model** determines vector dimension; your **Vayu Vector DB** collection must use the *same* size.
- Always use the *same* `EMBEDDING_MODEL` and `CHAT_MODEL` environment variables when running both ingestion and the chat app.
- API keys and base URL should never be committed to version control — set them in `ask-it/.env` (copy from `.env.example`).

---

## Navigation

| | |
|---|---|
| **Previous** | [← Step 2 — Vayu Vector DB](../02_vayu_vector_databases/) |
| **Next** | [Step 4 — Vayu RAG ingest lab →](../04_starter_kit/) |
| **Overview** | [Ask-It overview](../README.md) |
