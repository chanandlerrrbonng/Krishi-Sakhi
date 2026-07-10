# 🔎 Step 2 — Create your Vector Database (Qdrant)

**Ask-It** › **Vayu Vector DB (Qdrant)** · `02_vayu_vector_databases/`

> **Goal:** Set up a **Vayu Vector DB (Qdrant)** — the database that stores your documents as embeddings so they can be searched by meaning.

**What you'll do here:**
1. Create a Qdrant vector database in AI Studio
2. Wait until it's **Ready**
3. Configure firewall rules so external clients can reach its **public URL** (see **Port 443 FW Rule 5 1.pdf**)
4. Copy its URL and API key into `.env`

| [← Previous — Step 1 — Object Storage](../01_dataset/) | [Next — Step 3 — Model as a Service →](../03_vayu_model_as_a_service/) |
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

**Sample resource selections for your Qdrant Vector DB:**

| Parameter | Suggested selection |
|-----------|---------------------|
| **Engine (Type)** | Qdrant |
| **Version** | `v1.10.1` |
| **Compute Flavour** | General Purpose: **4 vCPU / 16GB RAM / cpu** (select **cpu** from the dropdown) |
| **Storage Flavour** | **SSD1-Persistent Storage** |
| **Storage Size** | **20 GB** |
| **Replica** | **1** |

> These are recommended minimum specs for development. Adjust as needed for your workload.

</details>

---

<details>
<summary><h3>2. Wait for Ready</h3></summary>

Submit the deployment and wait until the status shows **Ready**.

</details>

---

<details>
<summary><h3>3. Configure firewall access</h3></summary>

After the vector database is **Ready**, configure firewall rules so external clients can reach its **public URL**. See **Port 443 FW Rule 5 1.pdf** (provided to candidates).

</details>

---

<details>
<summary><h3>4. Copy your access details</h3></summary>

Note your **`QDRANT_URL`** and **`QDRANT_API_KEY`** from the **Connect** tab on your Vector DB resource.

> **Use the Public Endpoint** when your app runs outside the cluster (local Streamlit, ML Service, or a demo URL). Enable firewall rules first — see **Port 443 FW Rule 5 1.pdf**.

> **Important — clean up the URL:** when you copy `QDRANT_URL`, **remove `/dashboard` at the end** if present. Use the API root (e.g. `https://<your-host>`) — **not** `https://<your-host>/dashboard`.

</details>

---

<details>
<summary><h3>5. Save them to <code>.env</code></h3></summary>

At the `ask-it` repo root, edit `.env` (created in [Step 0](../00_vayu_workspace/)):

```bash
cd /home/jovyan/ask-it
# Edit .env — set QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME
```

`COLLECTION_NAME` defaults to `knowledge_base_rag` in `.env.example`. You can choose another name; the notebook creates the collection if it does not exist.

</details>

---

<details>
<summary><h3>6. (Optional) Local development</h3></summary>

For quick local testing without the hosted service, use on-disk Qdrant via the `QDRANT_PATH` variable in your notebook instead.

</details>

---

#### Resources

- [Provision Vayu Vector DB](https://ipcloud.tatacommunications.com/aistudio/#/experiment/vectordatabase-list)
- [Qdrant documentation](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/qdrant)
- [Milvus documentation](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/milvus)

| [← Previous — Step 1 — Object Storage](../01_dataset/) | [Overview](../README.md) | [Next — Step 3 — Model as a Service →](../03_vayu_model_as_a_service/) |
|:---|:---:|---:|
