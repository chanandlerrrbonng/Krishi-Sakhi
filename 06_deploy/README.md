# Step 6 — Deploy Ask-It as a hosted service

**Step 6 of 6**

<table width="100%" style="width:100%">
<tr>
<td align="left"><a href="../05_build_app/">Previous — Step 5 — Chat app</a></td>
<td align="right">Journey complete</td>
</tr>
</table>

> **Goal:** Take the chat app from Step 5, package it as a Docker image, sign it, and run it on **Vayu ML Service** — so anyone can open Ask-It from a URL without running anything locally.

**What you'll do here:**
1. Build and push a Docker image
2. Sign the image (required by Vayu)
3. Create an ML Service through the wizard
4. Verify the live URL works

> This step is optional but recommended if you want a shareable, always-on demo (e.g. for judges).

---

<details>
<summary><h3>🗺️ The big picture</h3></summary>

You'll deploy the **same** app you tested in Step 5. Nothing gets re-indexed — the container just *queries* the collection you already built.

| Piece | Where it comes from |
|-------|---------------------|
| Chat UI + RAG runtime | Docker image (`ask-it-chat:latest`) built from [`05_build_app/Dockerfile`](../05_build_app/Dockerfile) |
| Vector search | **Vayu Vector DB** — same `QDRANT_URL` / `QDRANT_API_KEY` as [Step 2](../02_vayu_vector_databases/) |
| Embeddings + chat | **Vayu Model as a Service** — same keys/models as [Step 3](../03_vayu_model_as_a_service/) |
| Indexed corpus | The Vector DB collection you built in [Step 4](../04_starter_kit/) |

> The container **does not** re-ingest documents. If you change `docs/`, re-run `qna.ipynb` before demoing.

</details>

---

<details>
<summary><h3>📋 Before you start</h3></summary>

| Step | You need |
|------|----------|
| [0](../00_vayu_workspace/) | Workspace with **Docker enabled** |
| [1](../01_dataset/) | Corpus in `docs/` (Object Storage sync optional) |
| [2](../02_vayu_vector_databases/) | `QDRANT_URL`, `QDRANT_API_KEY`, `COLLECTION_NAME` |
| [3](../03_vayu_model_as_a_service/) | `LLM_OPENAI_API_KEY`, `EMBEDDING_OPENAI_API_KEY`, `OPENAI_BASE_URL`, `EMBEDDING_MODEL`, `CHAT_MODEL` |
| [4](../04_starter_kit/) | `qna.ipynb` run — vectors in the Vector DB |
| [5](../05_build_app/) | Chat app tested locally and working |
| — | A container registry: username + CLI secret ([Container Registry guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/registry/)) |

Set these registry variables in the root [`.env`](../.env.example): `IMAGE_REGISTRY`, `REGISTRY_PROJECT`, `REGISTRY_USERNAME`, `REGISTRY_PASSWORD`, `VAYU_USERNAME`.

> **Optional automation:** [`image-signing/`](image-signing/) contains a helper script ([`sign_image.py`](image-signing/sign_image.py)) for the signing step.

</details>

---

<details>
<summary><h3>1. Build and push the Docker image</h3></summary>

> **Important:** build from the `ask-it/` folder, **not** `05_build_app/`. Building from the wrong folder will fail on `COPY`.

| | Path |
|---|------|
| **Build from** | `ask-it/` |
| **Dockerfile** | `ask-it/05_build_app/Dockerfile` |
| **Do NOT build from** | `05_build_app/` |

Log in to the registry and build + push in one go:

```bash
cd ask-it
set -a && source .env && set +a && echo "$REGISTRY_PASSWORD" | docker login "$IMAGE_REGISTRY" -u "$REGISTRY_USERNAME" --password-stdin

docker build -f 05_build_app/Dockerfile -t $IMAGE_REGISTRY/$REGISTRY_PROJECT/ask-it-chat:latest . --push
```

> Whenever you change registry variables in `.env`, re-run `set -a && source .env && set +a` (and the `docker login` line) — otherwise your shell keeps the old values.

Note the full image reference you pushed (e.g. `$IMAGE_REGISTRY/$REGISTRY_PROJECT/ask-it-chat:latest`) — you'll enter it in the wizard.

> If you push a **new** tag later, the previous tag must be **signed before** you push the new one (see the next section).

| Check | |
|-------|---|
| Port in image | **8501** (Streamlit; see `EXPOSE` in the Dockerfile) |
| Secrets | **Not** baked into the image — only passed at runtime |

</details>

---

<details>
<summary><h3>2. Sign the image</h3></summary>

Vayu ML Services only run **signed** images. Sign yours right after pushing.

Follow the [Container Registry guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/registry/) — especially **Steps 4–8** (signing certificates, `tcl-cosign` setup, sign, verify). Image to sign:

- `$IMAGE_REGISTRY/$REGISTRY_PROJECT/ask-it-chat:latest`

> **Prefer automation?** Use the [automated image signing guide](image-signing/README.md).

</details>

---

<details>
<summary><h3>3. Open Vayu ML Services</h3></summary>

Go to [Vayu ML Services](https://ipcloud.tatacommunications.com/aistudio/#/deploy/mlops-service-list).

For the full create wizard (Start → Infrastructure → Configure Compute → Observability → Review), see the [Creating ML Service guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/ml-service/#creating-ml-service).

</details>

---

<details>
<summary><h3>4. Create the ML Service (the wizard)</h3></summary>

Follow the wizard and map Ask-It's settings as below.

**4.1 Start — image and runtime**

| Field | Ask-It value |
|-------|--------------|
| **Name** | e.g. `ask-it-chat` or your team name |
| **Framework** | **Streamlit** (or **Python3** if Streamlit isn't listed — the image's CMD still runs `streamlit run`) |
| **Private Registry → Registry URL** | `$IMAGE_REGISTRY` (hostname only — no `https://`) |
| **Private Registry → Image** | The full signed image you pushed, e.g. `$IMAGE_REGISTRY/$REGISTRY_PROJECT/ask-it-chat:latest` |
| **Private Registry → Username / Password** | `$REGISTRY_USERNAME` / `$REGISTRY_PASSWORD` |
| **Port** | **8501** |
| **Public Expose** | Enable if you want a URL reachable outside the cluster (typical for demos) |

Leave **Args** empty unless your platform team specifies extra Streamlit flags.

**4.2 Environment variables (required)**

Add each key/value under **Environment Variable** on the Start step. Use the **same values** as your local `ask-it/.env` and your `qna.ipynb` ingest run. (The `.env` file is for local dev only — it is not baked into the image.)

| Key | Required | Source |
|-----|----------|--------|
| `QDRANT_URL` | Yes | [Step 2](../02_vayu_vector_databases/) |
| `QDRANT_API_KEY` | Yes | [Step 2](../02_vayu_vector_databases/) |
| `LLM_OPENAI_API_KEY` | Yes | [Step 3](../03_vayu_model_as_a_service/) |
| `EMBEDDING_OPENAI_API_KEY` | Yes | [Step 3](../03_vayu_model_as_a_service/) |
| `OPENAI_BASE_URL` | Yes | [Step 3](../03_vayu_model_as_a_service/) |
| `EMBEDDING_MODEL` | Yes | Must match ingest (e.g. `Qwen/Qwen3-Embedding-8B`) |
| `CHAT_MODEL` | Yes | Must match ingest (e.g. `openai/gpt-oss-120b`) |
| `COLLECTION_NAME` | Recommended | Default `knowledge_base_rag` |

Example (replace with your values):

```text
QDRANT_URL=<YOUR_QDRANT_URL>
QDRANT_API_KEY=<YOUR_QDRANT_API_KEY>
LLM_OPENAI_API_KEY=<YOUR_MAAS_API_KEY>
EMBEDDING_OPENAI_API_KEY=<YOUR_MAAS_API_KEY>
OPENAI_BASE_URL=<YOUR_MAAS_BASE_URL>
EMBEDDING_MODEL=<YOUR_EMBEDDING_MODEL>
CHAT_MODEL=<YOUR_CHAT_MODEL>
COLLECTION_NAME=knowledge_base_rag
```

> Do **not** set `QDRANT_PATH` for a hosted deployment unless you intentionally want on-disk Qdrant inside the container (not recommended here).

**4.3 Infrastructure**

Select the **Datacenter**, **Business Unit**, and **Environment** assigned to your workspace (same as your other Vayu resources).

**4.4 Configure compute**

| Field | Guidance |
|-------|----------|
| **Resources / flavor** | CPU is plenty for Streamlit + API calls; add GPU only if your track requires it |
| **Replicas** | `1` for a demo; increase for load testing |

**4.5 Observability**

Enable **Monitoring** and **Logging** if available — very helpful for debugging retrieval or MaaS errors during a demo.

**4.6 Review and submit**

Double-check the name, image, port **8501**, and all environment variables. Click **Submit** and wait until the status is **ready** on the ML Services list.

</details>

---

<details>
<summary><h3>🔍 Verify the endpoint</h3></summary>

1. Open **ML Services List** → click your service **Name**.
2. On **View ML Service**, check **Summary** and **Connect** for the public or internal URL.
3. Open the URL — you should see the Ask-It UI (same as local; see the [overview screenshot](../README.md#what-youll-build)).
4. Ask a question that exists in your docs (e.g. the field-trip reminder from `text-example.txt`).
5. Expand **Sources** on the reply — citations should match your [Step 4](../04_starter_kit/) ingest.

**If something's wrong:**

| Symptom | What to check |
|---------|---------------|
| Page does not load | Port **8501**, **Public Expose** enabled, pod status **ready** |
| "Failed to initialize RAG Engine" | Env vars match Steps 2–3; no typos in keys |
| Empty or wrong answers | Re-run `qna.ipynb`; `COLLECTION_NAME` and `EMBEDDING_MODEL` match ingest |
| Model errors | `CHAT_MODEL` / `OPENAI_BASE_URL` correct; API key valid and has credits |

</details>

---

<details>
<summary><h3>🗂️ Optional: Model Registry</h3></summary>

If your track requires registering the RAG configuration, register it at the [Vayu Model Registry](https://ipcloud.tatacommunications.com/aistudio/#/deploy/model-registry-list).

Register metadata like collection name, embedding model, chat model, and top-k — aligned with [`rag_client.py`](../05_build_app/rag_client.py). Deployment still runs through **ML Service** using the signed image from Step 1.

</details>

---

<details>
<summary><h3>✔️ Demo checklist (submission-ready)</h3></summary>

- [ ] Corpus indexed in Vector DB ([`04_starter_kit/qna.ipynb`](../04_starter_kit/qna.ipynb))
- [ ] Docker image built from `ask-it/`, pushed, and **signed**
- [ ] ML Service **ready** with port **8501** and all env vars set
- [ ] Public/demo URL opens the Ask-It UI
- [ ] Test question returns a grounded answer with **Sources** expanded
- [ ] Endpoint URL documented for judges (README or slide)

</details>

---

<details>
<summary><h3>🔑 Environment variable reference</h3></summary>

| Variable | Required | Notes |
|----------|----------|--------|
| `QDRANT_URL` | Yes (hosted) | From **Vayu Vector DB** |
| `QDRANT_API_KEY` | Yes (hosted) | From **Vayu Vector DB** |
| `QDRANT_PATH` | No | Local dev only — omit in ML Service |
| `LLM_OPENAI_API_KEY` | Yes | **MaaS** chat API key |
| `EMBEDDING_OPENAI_API_KEY` | Yes | **MaaS** embedding API key |
| `OPENAI_BASE_URL` | Yes | **MaaS** base URL |
| `EMBEDDING_MODEL` | Yes | Must match `qna.ipynb` ingest |
| `CHAT_MODEL` | Yes | Must match `qna.ipynb` ingest |
| `COLLECTION_NAME` | No | Default `knowledge_base_rag` |
| `IMAGE_REGISTRY` | Step 6 build | Registry host (no scheme) |
| `REGISTRY_PROJECT` | Step 6 build | Registry project name |
| `REGISTRY_USERNAME` | Step 6 build | `docker login` and signing |
| `REGISTRY_PASSWORD` | Step 6 build | `docker login` and signing |
| `VAYU_USERNAME` | Step 6 verify | Certificate identity for cosign verify |

</details>

---

<details>
<summary><h3>💡 Pro tips</h3></summary>

- **Re-deploy after env changes** — editing env vars usually requires a restart or new revision; confirm in the UI after saving.
- **Same models end to end** — changing `EMBEDDING_MODEL` without re-ingesting breaks vector search.
- **Watch your credits** — every question calls MaaS; use a smaller chat model for dry runs ([Step 3](../03_vayu_model_as_a_service/)).
- **Never commit secrets** — keep registry passwords and API keys in the platform UI or a secure store only.

</details>

---

<table width="100%" style="width:100%">
<tr>
<td align="left"><a href="../05_build_app/">Previous — Step 5 — Chat app</a></td>
<td align="center"><a href="../README.md">Overview</a></td>
<td align="right">Journey complete</td>
</tr>
</table>
