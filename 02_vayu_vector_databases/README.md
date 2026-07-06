# Step 2 — Create your Vector Database (Qdrant)

**Step 2 of 6** · [← Step 1 — Object Storage](../01_dataset/) · [🏠 Overview](../README.md) · [Step 3 — Models →](../03_vayu_model_as_a_service/)

> **Goal:** Set up a **Vayu Vector DB (Qdrant)** — the database that stores your documents as embeddings so they can be searched by meaning.

**What you'll do here:**
1. Create a Qdrant vector database in AI Studio
2. Wait until it's **Ready**
3. Copy its URL and API key into `.env`

---

## What is a vector database?

A normal database searches for exact words. A **vector database** searches by *meaning*. In [Step 4](../04_starter_kit/) you'll turn each document chunk into an embedding (a list of numbers), store it here, and later find the chunks closest in meaning to a user's question. **Qdrant** is the vector database engine you'll use.

Open it here: [Vayu Vector DB](https://ipcloud.tatacommunications.com/aistudio/#/experiment/vectordatabase-list).

---

## Step by step

1. **Create the database.** In AI Studio, click **Create Vector Database** and select the **Qdrant** engine under **Vector Type**. (See the [Creating Qdrant guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/qdrant/#creating-qdrant).)

2. **Wait for Ready.** Submit the deployment and wait until the status shows **Ready**.

3. **Copy your access details.** Note your **`QDRANT_URL`** and **`QDRANT_API_KEY`** from the console.

   > ⚠️ **Important — clean up the URL:** when you copy it, remove the trailing `dashboard` at the end. Use `https://<your-host>` — **not** `https://<your-host>/dashboard`.

4. **Save them to `.env`.** At the `ask-it` repo root:

   ```bash
   cd ask-it
   cp .env.example .env
   # Edit .env — set QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME
   ```

5. **(Optional) Local development.** For quick local testing without the hosted service, use on-disk Qdrant via the `QDRANT_PATH` variable in your notebook instead.

---

## ✅ You're done when

- Your Vector DB status shows **Ready**.
- `QDRANT_URL` (without the trailing `/dashboard`) and `QDRANT_API_KEY` are set in `ask-it/.env`.

---

## Resources

| Resource | URL |
|----------|-----|
| Provision Vayu Vector DB | https://ipcloud.tatacommunications.com/aistudio/#/experiment/vectordatabase-list |
| Docs (Qdrant) | https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/qdrant |
| Docs (Milvus) | https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/milvus |

---

## Navigation

| | | |
|:--|:--:|--:|
| [← Step 1 — Object Storage](../01_dataset/) | [🏠 Overview](../README.md) | [Step 3 — Model as a Service →](../03_vayu_model_as_a_service/) |
