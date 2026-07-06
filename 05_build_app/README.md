# Step 5 — Run the chat app locally

**Step 5 of 6** · [← Step 4 — Ingest lab](../04_starter_kit/) · [🏠 Overview](../README.md) · [Step 6 — Deploy →](../06_deploy/)

> **Goal:** Run the **Ask-It** chat app on your machine and ask questions about your indexed documents. This is where it all comes together.

**What you'll do here:**
1. Confirm your documents are indexed (Step 4) and `.env` is filled in
2. Start the Streamlit app
3. Open it in a browser and ask a question

> 💡 **Tip:** Each section below is collapsed. Click a heading to expand its details.

---

<details>
<summary><strong>🔄 How a question flows through the app</strong></summary>

<br>

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

<details>
<summary><strong>📁 What's in this folder</strong></summary>

<br>

| File | What it does |
|------|--------------|
| `chat_app.py` | The Streamlit chat interface |
| `rag_client.py` | The engine that does retrieval + LLM chat |
| `Dockerfile` | Used in [Step 6](../06_deploy/) to build the deployable image |

</details>

<details>
<summary><strong>📋 Before you start</strong></summary>

<br>

- [Step 4](../04_starter_kit/) is done — your documents are indexed in the Vector DB.
- `.env` has the values from [Step 2](../02_vayu_vector_databases/) (Vector DB) and [Step 3](../03_vayu_model_as_a_service/) (models).

</details>

<details>
<summary><strong>▶️ Run it</strong></summary>

<br>

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

</details>

<details>
<summary><strong>✅ You're done when</strong></summary>

<br>

- The app opens in your browser.
- You ask a question about your docs and get an answer with **Sources** you can expand.

Once local testing works, continue to [Step 6 — Deploy](../06_deploy/) to build, sign, and push the image as a hosted service.

</details>

<details>
<summary><strong>🔑 Environment variables</strong></summary>

<br>

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

<details>
<summary><strong>🛠️ Troubleshooting</strong></summary>

<br>

| Symptom | Fix |
|---------|-----|
| **Failed to initialize RAG Engine** | Check `.env` values; confirm Vector DB and MaaS credentials |
| Empty or wrong answers | Re-run `qna.ipynb`; verify `COLLECTION_NAME` and `EMBEDDING_MODEL` match ingest |
| Model errors | Confirm `CHAT_MODEL` / `OPENAI_BASE_URL`; check API key and credits |
| Page won't load in workspace | Use the proxy URL (`/proxy/8501`) instead of `localhost` |

</details>

<details>
<summary><strong>💡 Pro tips</strong></summary>

<br>

- **Re-run `qna.ipynb` after changing your documents** — otherwise the app searches stale data.
- **Never bake secrets into Docker images** — pass them as runtime environment variables in the ML Service (Step 6).

</details>

---

<p align="center"><a href="../README.md">🏠 Ask-It overview</a></p>

<table width="100%">
<tr>
<td align="left"><a href="../04_starter_kit/">← Step 4 — RAG ingest lab</a></td>
<td align="right"><a href="../06_deploy/">Step 6 — Deploy ML Service →</a></td>
</tr>
</table>
