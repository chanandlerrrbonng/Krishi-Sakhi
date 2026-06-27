# Step 3 — Vayu Model as a Service

**Ask-It** › **Vayu Model as a Service** · `03_vayu_model_as_a_service/`

|                      |                                                    |
|----------------------|----------------------------------------------------|
| **Previous**         | [← Step 2 — Vayu Vector DB](../02_vayu_vector_databases/) |
| **Next**             | [Step 4 — Vayu RAG ingest lab →](../04_starter_kit/) |

Set up **Vayu Model as a Service** for both text embeddings and chat completion.

---

## Quick Setup

1. **Open the Vayu Model as a Service catalog**  
   https://ai-gateway.cloudservices.tatacommunications.com/models/models/home
   Go to the Model Catalog in Vayu AI Studio.
2. **Pick your models**  
   - Choose an **embedding model** (for converting text to vectors).
   - Choose a **chat model** (for conversational/answering capabilities).
3. **Get API credentials**  
   - Copy your API key and the base endpoint URL from the catalog or your Workspace details.
4. **Export configuration variables**  
   Use these variables for both document ingestion (`qna.ipynb`) and for the chat app (`05_build_app/`):

   ```bash
   export OPENAI_BASE_URL="https://models.cloudservices.tatacommunications.com/v1"
   export CHAT_MODEL="openai/gpt-oss-20b"
   export LLM_OPENAI_API_KEY="sk-**********************"
   export EMBEDDING_MODEL="Qwen/Qwen3-Embedding-8B"
   export EMBEDDING_OPENAI_API_KEY="sk-**********************"
   ```

5. **Continue**  
   Go to [Step 4 — Vayu RAG ingest lab →](../04_starter_kit/) and run `qna.ipynb` in Vayu AI Studio.

---

## Key Points

- The **embedding model** determines vector dimension; your **Vayu Vector DB** collection must use the *same* size.
- Always use the *same* `EMBEDDING_MODEL` and `CHAT_MODEL` environment variables when running both ingestion and the chat app.
- API keys and base URL should never be committed to version control—export them in your shell or configure them via environment management tools.

---

## Where to Find More Info

- Detailed instructions are in the **Vayu Model as a Service** documentation in AI Studio (link from your tenant console).

---

## Navigation

|                      |                                                    |
|----------------------|----------------------------------------------------|
| **Previous**         | [← Step 2 — Vayu Vector DB](../02_vayu_vector_databases/) |
| **Next**             | [Step 4 — Vayu RAG ingest lab →](../04_starter_kit/) |
| **Overview**         | [Ask-It overview](../README.md)                    |
