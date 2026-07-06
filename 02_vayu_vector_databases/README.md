# 🔎 Step 2 — Create your Vector Database (Qdrant)

**Ask-It** › **Vayu Vector DB (Qdrant)** · `02_vayu_vector_databases/`

> **Goal:** Set up a **Vayu Vector DB (Qdrant)** — the database that stores your documents as embeddings so they can be searched by meaning.

**What you'll do here:**
1. Create a Qdrant vector database in AI Studio
2. Wait until it's **Ready**
3. Copy its URL and API key into `.env`

| [← Previous — Step 1 — Object Storage](../01_dataset/README.md) | [Next — Step 3 — Model as a Service →](../03_vayu_model_as_a_service/README.md) |
|:---|---:|

---

<details>
<summary><h3>🧠 What is a vector database?</h3></summary>

A normal database searches for exact words. A **vector database** searches by *meaning*. In [Step 4](../04_starter_kit/) you'll turn each document chunk into an embedding (a list of numbers), store it here, and later find the chunks closest in meaning to a user's question. **Qdrant** is the vector database engine you'll use.

Open it here: [Vayu Vector DB](https://ipcloud.tatacommunications.com/aistudio/#/experiment/vectordatabase-list).

</details>

---

<details>
<summary><h3>1. Create the database</h3></summary>

In AI Studio, click **Create Vector Database** and select the **Qdrant** engine under **Vector Type**. (See the [Creating Qdrant guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/qdrant/#creating-qdrant).)

</details>

---

<details>
<summary><h3>2. Wait for Ready</h3></summary>

Submit the deployment and wait until the status shows **Ready**.

</details>

---

<details>
<summary><h3>3. Copy your access details</h3></summary>

Note your **`QDRANT_URL`** and **`QDRANT_API_KEY`** from the console.

> **Important — clean up the URL:** when you copy it, remove the trailing `dashboard` at the end. Use `https://<your-host>` — **not** `https://<your-host>/dashboard`.

</details>

---

<details>
<summary><h3>4. Save them to <code>.env</code></h3></summary>

At the `ask-it` repo root:

```bash
cd ask-it
cp .env.example .env
# Edit .env — set QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME
```

</details>

---

<details>
<summary><h3>5. (Optional) Local development</h3></summary>

For quick local testing without the hosted service, use on-disk Qdrant via the `QDRANT_PATH` variable in your notebook instead.

</details>

---

#### Resources

- [Provision Vayu Vector DB](https://ipcloud.tatacommunications.com/aistudio/#/experiment/vectordatabase-list)
- [Qdrant documentation](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/qdrant)
- [Milvus documentation](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/milvus)

| [← Previous — Step 1 — Object Storage](../01_dataset/README.md) | [Overview](../README.md) | [Next — Step 3 — Model as a Service →](../03_vayu_model_as_a_service/README.md) |
|:---|:---:|---:|
