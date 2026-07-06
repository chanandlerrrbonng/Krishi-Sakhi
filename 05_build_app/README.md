# 🖥️ Step 5 — Run the chat app locally

**Ask-It** › **Streamlit (local)** · `05_build_app/`

> **Goal:** Run the **Ask-It** chat app on your machine and ask questions about your indexed documents. This is where it all comes together.

**What you'll do here:**
1. Confirm your documents are indexed (Step 4) and `.env` is filled in
2. Start the Streamlit app
3. Open it in a browser and ask a question

<table width="100%" style="width:100%">
<tr>
<td align="left"><a href="../04_starter_kit/">Previous — Step 4 — RAG ingest lab</a></td>
<td align="right"><a href="../06_deploy/">Next — Step 6 — Deploy</a></td>
</tr>
</table>

---

<details>
<summary><h3>🔄 How a question flows through the app</h3></summary>

```text
User question (chat_app.py)
        │
        ▼
Embed the question  (rag_client.py → Vayu Model as a Service)
        │
        ▼
Search the Vector DB  (the collection you built in Step 4)
        │
        ▼
LLM writes an answer + citations  (Vayu Model as a Service)
        │
        ▼
Shown in the Streamlit UI  (port 8501)
```

</details>

---

<details>
<summary><h3>📁 What's in this folder</h3></summary>

| File | What it does |
|------|--------------|
| `chat_app.py` | The Streamlit chat interface |
| `rag_client.py` | The engine that does retrieval + LLM chat |
| `Dockerfile` | Used in [Step 6](../06_deploy/) to build the deployable image |

</details>

---

<details>
<summary><h3>📋 Before you start</h3></summary>

- [Step 4](../04_starter_kit/) is done — your documents are indexed in the Vector DB.
- `.env` has the values from [Step 2](../02_vayu_vector_databases/) (Vector DB) and [Step 3](../03_vayu_model_as_a_service/) (models).

</details>

---

<details>
<summary><h3>▶️ Run it</h3></summary>

If your environment is already set up (from [Step 0](../00_vayu_workspace/)):

```bash
cd ask-it
source .venv/bin/activate   # if not already active

cd 05_build_app
streamlit run chat_app.py
```

If you're starting fresh:

```bash
python3 -m venv .venv
source .venv/bin/activate
cd ask-it
pip install -r requirements.txt

cp .env.example .env
# Fill in your Vector DB and Model as a Service credentials

cd 05_build_app
streamlit run chat_app.py
```

Then:

- Open **http://localhost:8501** in your browser.
- Inside a **Vayu AI Studio workspace**, use the proxy URL instead (e.g. `https://<your-workspace-host>/proxy/8501`).
- Adjust **Top-K** in the sidebar to control how many document chunks are retrieved.
- Expand **Sources** under any answer to see where it came from.

> Once local testing works, continue to [Step 6 — Deploy](../06_deploy/) to build, sign, and push the image as a hosted service.

</details>

---

<details>
<summary><h3>🔑 Environment variables</h3></summary>

| Variable | Required | Used by | Purpose |
|----------|----------|---------|---------|
| `QDRANT_URL` | Yes | `rag_client.py` | Vayu Vector DB endpoint |
| `QDRANT_API_KEY` | Yes | `rag_client.py` | Vector DB auth |
| `LLM_OPENAI_API_KEY` | Yes | `rag_client.py` | MaaS chat API key |
| `EMBEDDING_OPENAI_API_KEY` | Yes | `rag_client.py` | MaaS embedding API key |
| `OPENAI_BASE_URL` | Yes | `rag_client.py` | MaaS base URL |
| `EMBEDDING_MODEL` | Yes | `rag_client.py` | Must match ingest |
| `CHAT_MODEL` | Yes | `rag_client.py` | Must match ingest |
| `COLLECTION_NAME` | No | `rag_client.py` | Default `knowledge_base_rag` |

</details>

---

<details>
<summary><h3>🛠️ Troubleshooting</h3></summary>

| Symptom | Fix |
|---------|-----|
| **Failed to initialize RAG Engine** | Check `.env` values; confirm Vector DB and MaaS credentials |
| Empty or wrong answers | Re-run `qna.ipynb`; verify `COLLECTION_NAME` and `EMBEDDING_MODEL` match ingest |
| Model errors | Confirm `CHAT_MODEL` / `OPENAI_BASE_URL`; check API key and credits |
| Page won't load in workspace | Use the proxy URL (`/proxy/8501`) instead of `localhost` |

</details>

---

<details>
<summary><h3>💡 Pro tips</h3></summary>

- **Re-run `qna.ipynb` after changing your documents** — otherwise the app searches stale data.
- **Never bake secrets into Docker images** — pass them as runtime environment variables in the ML Service (Step 6).

</details>

---

<table width="100%" style="width:100%">
<tr>
<td align="left"><a href="../04_starter_kit/">Previous — Step 4 — RAG ingest lab</a></td>
<td align="center"><a href="../README.md">Overview</a></td>
<td align="right"><a href="../06_deploy/">Next — Step 6 — Deploy</a></td>
</tr>
</table>
