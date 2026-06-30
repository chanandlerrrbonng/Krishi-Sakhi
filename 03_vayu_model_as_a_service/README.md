# Step 3 — Vayu Model as a Service

**Ask-It** › **Vayu Model as a Service** · `03_vayu_model_as_a_service/`

| | |
|---|---|
| **Previous** | [← Step 2 — Vayu Vector DB](../02_vayu_vector_databases/) |
| **Next** | [Step 4 — Vayu RAG ingest lab →](../04_starter_kit/) |

Set up **Vayu Model as a Service** for both text embeddings and chat completion.

Ask-It uses **two models** (one embedding, one LLM) and **two API keys** — create a separate key for each model.

---

## Quick Setup

### 1. Explore and pick models

Open the **Explore Models** tab in the Model as a Service catalog:

[Explore Models](https://ai-gateway.cloudservices.tatacommunications.com/models/models/explore)

Choose which models you want to use:

- One **embedding model** (for converting text to vectors)
- One **chat / LLM model** (for answering questions)

You will get the exact model IDs in step 3 via the `/v1/models` API.

### 2. Create API keys

Open the **Secret Key** list:

[API keys — Secret Key list](https://ai-gateway.cloudservices.tatacommunications.com/models/models/user/secret-key-list)

Click **Create API key** and create **two keys**:

| Key | Use for | Maps to `.env` |
|-----|---------|----------------|
| Embedding key | Your chosen embedding model | `EMBEDDING_OPENAI_API_KEY` |
| LLM key | Your chosen chat model | `LLM_OPENAI_API_KEY` |

Create one API key per model (embedding and LLM).

### 3. Get model IDs

Call the `/v1/models` endpoint on your **OpenAI-compatible base URL**, using the matching API key for each call:

```bash
# Embedding models — use your embedding API key
curl https://models.cloudservices.tatacommunications.com/v1/models \
  -H "Authorization: Bearer <EMBEDDING_API_KEY>"

# Chat / LLM models — use your LLM API key
curl https://models.cloudservices.tatacommunications.com/v1/models \
  -H "Authorization: Bearer <LLM_API_KEY>"
```

Replace `<EMBEDDING_API_KEY>` and `<LLM_API_KEY>` with the keys you created in step 2. From each response, pick the model ID that matches your choices from step 1 and set them as `EMBEDDING_MODEL` and `CHAT_MODEL` in `.env`.

If your tenant uses a different host, use your `OPENAI_BASE_URL` value instead (e.g. `"${OPENAI_BASE_URL}/models"`).

### 4. Configure `.env`

At the **ask-it** repo root, copy `.env.example` to `.env` and set:

```bash
cd ask-it
cp .env.example .env
```

| Variable | Value |
|----------|--------|
| `OPENAI_BASE_URL` | Your MaaS OpenAI-compatible base URL (e.g. `https://models.cloudservices.tatacommunications.com/v1`) |
| `EMBEDDING_OPENAI_API_KEY` | API key created for the **embedding** model |
| `LLM_OPENAI_API_KEY` | API key created for the **LLM** model |
| `EMBEDDING_MODEL` | Embedding model ID from the `/v1/models` response (step 3) |
| `CHAT_MODEL` | Chat model ID from the `/v1/models` response (step 3) |

These variables are used by `qna.ipynb` and `05_build_app/`.

### 5. Continue

Go to [Step 4 — Vayu RAG ingest lab →](../04_starter_kit/) and run `qna.ipynb` in Vayu AI Studio.

---

## Key Points

- Create **one API key per model** — embedding and LLM keys are separate in this template.
- The **embedding model** determines vector dimension; your **Vayu Vector DB** collection must use the *same* size.
- Always use the *same* `EMBEDDING_MODEL`, `CHAT_MODEL`, and API keys when running both ingestion and the chat app.
- Never commit API keys to version control — set them only in `ask-it/.env`.

---

## Navigation

| | |
|---|---|
| **Previous** | [← Step 2 — Vayu Vector DB](../02_vayu_vector_databases/) |
| **Next** | [Step 4 — Vayu RAG ingest lab →](../04_starter_kit/) |
| **Overview** | [Ask-It overview](../README.md) |
