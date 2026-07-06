# Step 3 — Get your model API keys (Model as a Service)

**Step 3 of 6**

> **Goal:** Get access to the two AI models Ask-It needs — one to create embeddings and one to answer questions — through **Vayu Model as a Service (MaaS)**.

**What you'll do here:**
1. Pick an embedding model and a chat model from the catalog
2. Create **two** API keys (one per model)
3. Look up the exact model IDs
4. Save everything into `.env`

> 💡 **Tip:** Each section below is collapsed. Click a heading to expand its details.

---

<details>
<summary><strong>🤔 Why two models and two keys?</strong></summary>

<br>

Ask-It uses **two** models:

- An **embedding model** — turns text into vectors (numbers that capture meaning). Used to index your docs and to understand questions.
- A **chat model (LLM)** — reads the retrieved text and writes the final answer.

You'll create a **separate API key for each**. MaaS gives you an OpenAI-compatible API, so the code talks to both using familiar OpenAI-style calls.

See the [Model as a Service overview](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/model-as-a-service/maas-intro) for background.

</details>

<details>
<summary><strong>1️⃣ Pick your two models</strong></summary>

<br>

Open the **Explore Models** catalog: [Explore Models](https://ai-gateway.cloudservices.tatacommunications.com/models/models/explore) ([guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/model-as-a-service/maas-explore-models)).

Choose:

- One **embedding model** (converts text to vectors)
- One **chat / LLM model** (answers questions)

You'll get the exact model IDs in step 3 below.

</details>

<details>
<summary><strong>2️⃣ Create two API keys</strong></summary>

<br>

Open the **Secret Key** list: [API keys](https://ai-gateway.cloudservices.tatacommunications.com/models/models/user/secret-key-list) ([guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/model-as-a-service/maas-api-keys)).

Click **Create API key** twice to make one key per model:

| Key | Use it for | Goes into `.env` as |
|-----|------------|---------------------|
| Embedding key | Your embedding model | `EMBEDDING_OPENAI_API_KEY` |
| LLM key | Your chat model | `LLM_OPENAI_API_KEY` |

</details>

<details>
<summary><strong>3️⃣ Find the exact model IDs</strong></summary>

<br>

Ask the API which models are available, using each key. Replace the placeholders with your keys:

```bash
# Embedding models — use your embedding API key
curl https://models.cloudservices.tatacommunications.com/v1/models \
  -H "Authorization: Bearer <EMBEDDING_API_KEY>"

# Chat / LLM models — use your LLM API key
curl https://models.cloudservices.tatacommunications.com/v1/models \
  -H "Authorization: Bearer <LLM_API_KEY>"
```

From each response, copy the model ID that matches your choices from step 1. These become `EMBEDDING_MODEL` and `CHAT_MODEL`.

> If your tenant uses a different host, use your `OPENAI_BASE_URL` value instead (e.g. `"${OPENAI_BASE_URL}/models"`).

</details>

<details>
<summary><strong>4️⃣ Fill in <code>.env</code></strong></summary>

<br>

At the `ask-it` repo root:

```bash
cd ask-it
cp .env.example .env
```

Then set:

| Variable | Value |
|----------|--------|
| `OPENAI_BASE_URL` | Your MaaS base URL (e.g. `https://models.cloudservices.tatacommunications.com/v1`) |
| `EMBEDDING_OPENAI_API_KEY` | The **embedding** model's API key |
| `LLM_OPENAI_API_KEY` | The **chat** model's API key |
| `EMBEDDING_MODEL` | Embedding model ID (from step 3) |
| `CHAT_MODEL` | Chat model ID (from step 3) |

These are used by `qna.ipynb` (Step 4) and the app in `05_build_app/` (Steps 5–6).

</details>

<details>
<summary><strong>📌 Things to remember</strong></summary>

<br>

- **One API key per model** — embedding and LLM keys are kept separate in this template.
- **The embedding model sets the vector size** — your Vector DB collection ([Step 2](../02_vayu_vector_databases/)) must match it. Change the embedding model later and you'll need to recreate the collection.
- **Stay consistent** — use the *same* models and keys for both ingestion (Step 4) and the chat app (Steps 5–6).
- **Never commit API keys** — set them only in `ask-it/.env`.

</details>

<details>
<summary><strong>📚 Documentation</strong></summary>

<br>

| Topic | Link |
|-------|------|
| Overview | [MaaS introduction](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/model-as-a-service/maas-intro) |
| Explore models | [Explore Models guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/model-as-a-service/maas-explore-models) |
| API keys | [API Key Management](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/model-as-a-service/maas-api-keys) |
| Playground | [Playground](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/model-as-a-service/maas-playground) |
| Dashboard | [Dashboard](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/model-as-a-service/maas-dashboard) |
| LLM providers | [LLM Provider List](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/model-as-a-service/maas-llm-providers) |

</details>

---

<p align="center"><a href="../README.md">🏠 Ask-It overview</a></p>

<table width="100%">
<tr>
<td align="left"><a href="../02_vayu_vector_databases/">← Step 2 — Vector DB</a></td>
<td align="right"><a href="../04_starter_kit/">Step 4 — RAG ingest lab →</a></td>
</tr>
</table>
