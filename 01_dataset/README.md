# Step 1 — Vayu Object Storage (dataset)

**Ask-It** › **Vayu Object Storage** · `01_dataset/`

| | |
|---|---|
| **Previous** | [Step 0 — Vayu AI Studio Workspace](../00_vayu_workspace/) |
| **Next** | [Step 2 — Vayu Vector DB →](../02_vayu_vector_databases/) |

Welcome! This folder contains your starting document corpus and scripts to sync it with **Vayu Object Storage** — essential for seamless downstream ingestion and RAG workflows in Vayu AI Studio.

**Reference docs:** [Vayu S3 Object Storage Documentation](https://ipcloud.tatacommunications.com/docs/docs/s3-object-browser/)

---

## Folder Contents

| File / Folder | Purpose |
|---------------|---------|
| `docs/` | Sample knowledge base: `.md`, `.txt`, `.html` included |
| `01_dataset.ipynb` | Jupyter notebook: sync `docs/` to/from an S3 bucket (boto3) |

---

## Step-by-Step: Sync your Docs

> **Tip:** Maintain the same folder structure locally and in the bucket to ensure source citations work end-to-end.

1. **Set required environment variables** in `ask-it/.env` (copy from `.env.example` — do not paste credentials into notebook cells):

   ```bash
   cd ask-it
   cp .env.example .env
   # Edit .env — VAYU_S3_KEY, VAYU_S3_SECRET, VAYU_S3_ENDPOINT, VAYU_S3_BUCKET
   # Optional: S3_PREFIX=docs/
   ```

   | Variable | Purpose |
   |----------|---------|
   | `VAYU_S3_KEY` | S3 access key ID |
   | `VAYU_S3_SECRET` | S3 secret access key |
   | `VAYU_S3_ENDPOINT` | Vayu Object Storage endpoint URL |
   | `VAYU_S3_BUCKET` | Target bucket name |

   _(Never commit real credentials!)_

2. **Run the notebook**

   Open [`01_dataset.ipynb`](01_dataset.ipynb), then select the kernel:

   1. Open **Select Kernel** and choose **Python Environments**.

   ![Select Kernel — Python Environments](../assets/kernel_select.png)

   2. Under **Select a Python Environment**, pick the **Recommended** environment (it should point to the `.venv` from [Step 0](../00_vayu_workspace/)).

   ![Select a Python Environment](../assets/Select_kernerl_env.png)

   Use the Upload/Download cells to move the corpus (`docs/`) between your local disk and Vayu Object Storage.

3. **Continue project steps**

   Once uploaded, open [`04_starter_kit/qna.ipynb`](../04_starter_kit/qna.ipynb) for ingest.

   **Paths depend on where the notebook runs** — you usually do **not** change anything in this folder:

   | You are here | Corpus path | Why |
   |--------------|-------------|-----|
   | `01_dataset/` (`01_dataset.ipynb`) | `docs` or `Path("docs")` | Corpus is **in this folder** — already set in the notebook as `LOCAL_FOLDER = "docs"` |
   | `04_starter_kit/` (`qna.ipynb`) | `Path("../01_dataset/docs")` | Notebook is one level up from `01_dataset/` |

   Do **not** use `../01_dataset/docs` inside `01_dataset.ipynb` — that would point outside this step’s folder.

---

## Sample Corpus

| Example File | Description |
|--------------|-------------|
| `text-example.txt` | Field-trip reminder note |
| `markdown-example.md` | Short markdown sample |
| `html-example.html` | Minimal HTML file |

**Supported ingest extensions:** `.md`, `.markdown`, `.txt`, `.html`, `.htm`, `.rst`, `.csv`

---

## Best Practices

- **Never commit** storage credentials to git or share them in public repos.
- Consistent structure: keep the `docs/` layout identical in local and remote locations to enable accurate citations and easier debugging.

---

## Navigation

| | |
|---|---|
| **Previous** | [Step 0 — Vayu AI Studio Workspace](../00_vayu_workspace/) |
| **Next** | [Step 2 — Vayu Vector DB →](../02_vayu_vector_databases/) |
