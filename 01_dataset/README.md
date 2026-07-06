# Step 1 — Upload your documents (Vayu Object Storage)

**Step 1 of 6** · [← Step 0 — Workspace](../00_vayu_workspace/) · [🏠 Overview](../README.md) · [Step 2 — Vector DB →](../02_vayu_vector_databases/)

> **Goal:** Store the documents your assistant will answer from in **Vayu Object Storage**, so the notebooks in later steps can read them.

**What you'll do here:**
1. Set your storage credentials in `.env`
2. Run a notebook to upload the sample documents to a cloud bucket
3. Confirm the files landed in the S3 Browser

> This step is **optional** — you can also just keep documents in the local `docs/` folder. But uploading to Object Storage is closer to a real project and useful if your team shares a corpus.

---

## What's in this folder

| File / Folder | What it's for |
|---------------|---------------|
| `docs/` | A small sample knowledge base (`.md`, `.txt`, `.html`) to get you started |
| `01_dataset.ipynb` | A notebook that syncs `docs/` to/from a cloud storage bucket |

---

## Step by step

> **Tip:** Keep the same folder structure locally and in the bucket. This keeps source citations working end to end.

### 1. Add your storage credentials

Set these values in `ask-it/.env` (copy from `.env.example` first — never paste credentials into notebook cells):

```bash
cd ask-it
cp .env.example .env
# Edit .env — set VAYU_S3_KEY, VAYU_S3_SECRET, VAYU_S3_ENDPOINT, VAYU_S3_BUCKET
```

| Variable | What it is |
|----------|------------|
| `VAYU_S3_KEY` | S3 access key ID |
| `VAYU_S3_SECRET` | S3 secret access key |
| `VAYU_S3_ENDPOINT` | Vayu Object Storage endpoint URL |
| `VAYU_S3_BUCKET` | The bucket to upload to |

> ⚠️ Never commit real credentials to git.

### 2. Run the notebook

Open [`01_dataset.ipynb`](01_dataset.ipynb), then select the kernel:

1. Open **Select Kernel** → **Python Environments**.

   ![Select Kernel — Python Environments](../assets/kernel_select.png)

2. Pick the **Recommended** environment (it should point to the `.venv` from [Step 0](../00_vayu_workspace/)).

   ![Select a Python Environment](../assets/Select_kernerl_env.png)

3. Confirm the interpreter path ends with `<your-env-name>/bin/python` (e.g. `.venv/bin/python`).

Then run the **Upload** cell to send `docs/` to Object Storage. (The **Download** cell does the reverse, if you ever need to pull the corpus back.)

### 3. Verify the upload

Open the [Vayu Cloud Storage S3 Browser](https://ipcloud.tatacommunications.com/cloud/console/vcs/#/vcs/s3-browser) and check your files:

1. Open the bucket named in **`VAYU_S3_BUCKET`**.
2. Go to **`ask-it/docs/`**.
3. Confirm your files are there (e.g. `text-example.txt`, `markdown-example.md`, `html-example.html`).

---

## ✅ You're done when

- The upload cell finished without errors.
- You can see your files under `ask-it/docs/` in the S3 Browser.

---

## The sample corpus

| Example file | Description |
|--------------|-------------|
| `text-example.txt` | Field-trip reminder note |
| `markdown-example.md` | Short markdown sample |
| `html-example.html` | Minimal HTML file |

**Supported file types for ingest:** `.md`, `.markdown`, `.txt`, `.html`, `.htm`, `.rst`, `.csv`

> Want to use your own documents? Drop them into `docs/` (in one of the supported formats) and re-run the upload cell.

---

## Best practices

- **Never commit** storage credentials to git or share them publicly.
- **Mirror your structure** — keep the local `docs/` layout identical under `ask-it/docs/` in the bucket. This makes citations accurate and debugging easier.

---

## Navigation

| | | |
|:--|:--:|--:|
| [← Step 0 — Workspace](../00_vayu_workspace/) | [🏠 Overview](../README.md) | [Step 2 — Vayu Vector DB →](../02_vayu_vector_databases/) |
