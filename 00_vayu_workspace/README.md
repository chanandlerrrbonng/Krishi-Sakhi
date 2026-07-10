# 🧑‍💻 Step 0 — Set up your Vayu Workspace

**Ask-It** › **Vayu AI Studio Workspace** · `00_vayu_workspace/`

> **Goal:** Create a place in the cloud (a "workspace") where you'll run the notebooks and the chat app for the rest of this project.

**What you'll do here:**
1. Create a Vayu AI Studio workspace (with Docker and public access enabled)
2. Clone this `ask-it` repository into `/home/jovyan`
3. Install the Python dependencies and create `.env`
4. Pick the right kernel for the notebooks

You only do this step once.

| [← Previous — Ask-It overview](../README.md) | [Next — Step 1 — Object Storage →](../01_dataset/) |
|:---|---:|

---

<details>
<summary><h3>🧭 What is a "workspace"?</h3></summary>

A **Vayu AI Studio workspace** is a ready-to-use cloud computer with a terminal, a code editor, and Jupyter notebooks. Instead of setting up Python on your own laptop, you do everything inside this workspace.

![Vayu AI Studio Workspace Overview](../assets/workspaces.png)

</details>

---

<details>
<summary><h3>1. Create the workspace</h3></summary>

> **Already have a workspace?** If one was provided to you, skip straight to the next section.

1. Log in to [Vayu AI Studio → Workspaces](https://ipcloud.tatacommunications.com/aistudio/#/build/workspace-list).
2. Click **Create Workspace** and follow the wizard (Start → Infrastructure → Configure Compute and Storage → Observability → Review). The [Creating Workspace guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/workspace/#creating-workspace) walks through each screen.
3. **Add an object storage host alias:** during creation, add a **host alias** for object storage using the **IP** and **endpoint** from the **Access Guide**. Enter the endpoint as the hostname **only** — no `http://` or `https://`.
4. **Turn on "Enable Docker in the Workspace"** before you finish. This is required later for [Step 5](../05_build_app/) and [Step 6](../06_deploy/).
5. **Public access:** enable the **Public Access** toggle in the workspace wizard.
6. **Configure compute and storage (recommended):** on the **Configure Compute and Storage** step:
   - **Flavor:** **4 vCPU / 8GB RAM / cpu** from **General Purpose** flavors (choose **cpu** from the dropdown)
   - **Billing Mode:** **Hourly**
   - **Storage Flavor:** **SSD1-Persistent Storage**
   - **Billing Mode for Storage:** **Monthly**
   - **Size:** **5**

   Change these if your workload needs more resources.
7. Submit the workspace and wait until the status shows **Ready**.
8. Configure firewall rules. Follow **`Port 443 FW Rule 5 1.pdf`** (provided to candidates).
9. To access the workspace, open the **Connect** tab on the workspace detail page and open the **Public Endpoint**.

</details>

---

<details>
<summary><h3>2. Get the code into your workspace</h3></summary>

Open the workspace terminal and clone this repository into `/home/jovyan`:

```bash
cd /home/jovyan
git clone https://ailab.cloudservices.tatacommunications.com/code/vayu-hackathon/ask-it.git
```

(Or upload the folder manually through the UI.)

</details>

---

<details>
<summary><h3>3. Install dependencies</h3></summary>

Still in the terminal, set up a Python virtual environment and install the packages:

```bash
cd /home/jovyan
python3 -m venv .venv
source .venv/bin/activate
cd ask-it
pip install -r requirements.txt

cp .env.example .env
# You'll fill in .env with credentials from the Access Guide and Steps 2–3 (and Step 6)
```

> A **virtual environment** (`.venv`) keeps this project's packages separate from everything else. The `source .venv/bin/activate` line "turns it on" — you'll run it each time you open a new terminal.

</details>

---

<details>
<summary><h3>4. Select the notebook kernel</h3></summary>

Whenever you open a notebook (`.ipynb`) in this project, tell it to use the `.venv` you just created:

1. Open **Select Kernel** and choose **Python Environments**.

   ![Select Kernel — Python Environments](../assets/kernel_select.png)

2. Pick the **Recommended** environment (it should point to your new `.venv`).

   ![Select a Python Environment](../assets/Select_kernerl_env.png)

3. **Double-check the path:** the selected interpreter should end with `<your-env-name>/bin/python` — for example, `.venv/bin/python`.

</details>

---

<details>
<summary><h3>🧭 Where you'll work next</h3></summary>

You'll use this workspace for:

- [Step 1 — Vayu Object Storage](../01_dataset/) (upload your documents)
- [Step 4 — RAG ingest notebook](../04_starter_kit/qna.ipynb)
- [Step 5 — Chat app & deploy](../05_build_app/)

</details>

---

#### Resources

- [Vayu AI Studio Workspace Dashboard](https://ipcloud.tatacommunications.com/aistudio/#/build/workspace-list)
- [Workspace documentation](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/workspace/)
- **`Port 443 FW Rule 5 1.pdf`** (provided to candidates)

| [← Previous — Ask-It overview](../README.md) | [Overview](../README.md) | [Next — Step 1 — Object Storage →](../01_dataset/) |
|:---|:---:|---:|
