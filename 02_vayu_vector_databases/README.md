# Step 2 — Create your Vector Database (Qdrant)

**Step 2 of 6**

> **Goal:** Set up a **Vayu Vector DB (Qdrant)** — the database that stores your documents as embeddings so they can be searched by meaning.

**What you'll do here:**
1. Create a Qdrant vector database in AI Studio
2. Wait until it's **Ready**
3. Copy its URL and API key into `.env`

> 💡 **Tip:** Each section below is collapsed. Click a heading to expand its details.

---

<details>
<summary><strong>🧠 What is a vector database?</strong></summary>

<br>

A normal database searches for exact words. A **vector database** searches by *meaning*. In [Step 4](../04_starter_kit/) you'll turn each document chunk into an embedding (a list of numbers), store it here, and later find the chunks closest in meaning to a user's question. **Qdrant** is the vector database engine you'll use.

Open it here: [Vayu Vector DB](https://ipcloud.tatacommunications.com/aistudio/#/experiment/vectordatabase-list).

</details>

<details>
<summary><strong>1️⃣ Create the database</strong></summary>

<br>

In AI Studio, click **Create Vector Database** and select the **Qdrant** engine under **Vector Type**. (See the [Creating Qdrant guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/qdrant/#creating-qdrant).)

</details>

<details>
<summary><strong>2️⃣ Wait for Ready</strong></summary>

<br>

Submit the deployment and wait until the status shows **Ready**.

</details>

<details>
<summary><strong>3️⃣ Copy your access details</strong></summary>

<br>

Note your **`QDRANT_URL`** and **`QDRANT_API_KEY`** from the console.

> ⚠️ **Important — clean up the URL:** when you copy it, remove the trailing `dashboard` at the end. Use `https://<your-host>` — **not** `https://<your-host>/dashboard`.

</details>

<details>
<summary><strong>4️⃣ Save them to <code>.env</code></strong></summary>

<br>

At the `ask-it` repo root:

```bash
cd ask-it
cp .env.example .env
# Edit .env — set QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME
```

</details>

<details>
<summary><strong>5️⃣ (Optional) Local development</strong></summary>

<br>

For quick local testing without the hosted service, use on-disk Qdrant via the `QDRANT_PATH` variable in your notebook instead.

</details>

<details>
<summary><strong>✅ You're done when</strong></summary>

<br>

- Your Vector DB status shows **Ready**.
- `QDRANT_URL` (without the trailing `/dashboard`) and `QDRANT_API_KEY` are set in `ask-it/.env`.

</details>

<details>
<summary><strong>🔗 Resources</strong></summary>

<br>

| Resource | URL |
|----------|-----|
| Provision Vayu Vector DB | https://ipcloud.tatacommunications.com/aistudio/#/experiment/vectordatabase-list |
| Docs (Qdrant) | https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/qdrant |
| Docs (Milvus) | https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/milvus |

</details>

---

<p align="center"><a href="../README.md">🏠 Ask-It overview</a></p>

<table width="100%">
<tr>
<td align="left"><a href="../01_dataset/">← Step 1 — Object Storage</a></td>
<td align="right"><a href="../03_vayu_model_as_a_service/">Step 3 — Model as a Service →</a></td>
</tr>
</table>
