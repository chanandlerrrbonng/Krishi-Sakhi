# Step 0 — Vayu Object Storage (dataset)

**Ask-It** › **Vayu Object Storage** · `00_dataset/`

| | |
|---|---|
| **Previous** | [Ask-It overview](../README.md) |
| **Next** | [Step 1 — Vayu AI Studio Workspace →](../01_vayu_workspace/) |

Welcome! This folder contains your starting document corpus and scripts to sync it with **Vayu Object Storage** — essential for seamless downstream ingestion and RAG workflows in Vayu AI Studio.

📄 **Reference docs:**  
- [Vayu S3 Object Storage Documentation](https://ipcloud.tatacommunications.com/docs/docs/s3-object-browser/)

---

## Folder Contents

| File / Folder         | Purpose                                                    |
|----------------------|------------------------------------------------------------|
| `docs/`              | Sample knowledge base: `.md`, `.txt`, `.html` included     |
| `00_dataset.ipynb`   | Jupyter notebook: sync `docs/` to/from an S3 bucket (boto3)|

---

## Step-by-Step: Sync your Docs

> 🗂️ **Tip:** Maintain the same folder structure locally and in the bucket to ensure source citations work end-to-end.

1. **Set required environment variables** (export in your shell or AI Studio secrets — do not paste credentials into notebook cells):

   ```bash
   export VAYU_S3_KEY="<your-access-key>"
   export VAYU_S3_SECRET="<your-secret-key>"
   export VAYU_S3_ENDPOINT="<your-s3-endpoint>"
   export VAYU_S3_BUCKET="<your-bucket-name>"
   export S3_PREFIX="docs/"   # optional; default in notebook is docs/
   ```

   | Variable | Purpose |
   |----------|---------|
   | `VAYU_S3_KEY` | S3 access key ID |
   | `VAYU_S3_SECRET` | S3 secret access key |
   | `VAYU_S3_ENDPOINT` | Vayu Object Storage endpoint URL |
   | `VAYU_S3_BUCKET` | Target bucket name |

   _(Never commit real credentials!)_

2. **Run the Notebook:**  
   If running locally, set up the project environment first:

   Then use the Upload/Download cells in `00_dataset.ipynb` to move the corpus (`docs/`) between your local disk and Vayu Object Storage.

3. **Continue Project Steps:**  
   Once uploaded, open [`04_starter_kit/qna.ipynb`](../04_starter_kit/qna.ipynb) for ingest.

   **Paths depend on where the notebook runs** — you usually do **not** change anything in this folder:

   | You are here | Corpus path | Why |
   |--------------|-------------|-----|
   | `00_dataset/` (`00_dataset.ipynb`) | `docs` or `Path("docs")` | Corpus is **in this folder** — already set in the notebook as `LOCAL_FOLDER = "docs"` |
   | `04_starter_kit/` (`qna.ipynb`) | `Path("../00_dataset/docs")` | Notebook is one level up from `00_dataset/` |

   Do **not** use `../00_dataset/docs` inside `00_dataset.ipynb` — that would point outside this step’s folder. The ingest notebook already uses the relative path above when run from `04_starter_kit/`.

---

## Sample Corpus

| Example File            | Description              |
|------------------------|--------------------------|
| `text-example.txt`      | Field-trip reminder note |
| `markdown-example.md`   | Short markdown sample    |
| `html-example.html`     | Minimal HTML file        |

> **Supported ingest extensions:**  
> `.md`, `.markdown`, `.txt`, `.html`, `.htm`, `.rst`, `.csv`

---

## Best Practices

- **Never commit** storage credentials to git or share them in public repos.
- Consistent structure: keep the `docs/` layout identical in local and remote locations to enable accurate citations and easier debugging.

---

## Navigation

| | |
|---|---|
| **Previous** | [Ask-It overview](../README.md) |
| **Next** | [Step 1 — Vayu AI Studio Workspace →](../01_vayu_workspace/) |
