# Step 0 — Set up your Vayu Workspace

**Step 0 of 6**

<table width="100%" style="width:100%">
<tr>
<td align="left"><a href="../README.md">Previous — Ask-It overview</a></td>
<td align="right"><a href="../01_dataset/">Next — Step 1 — Object Storage</a></td>
</tr>
</table>

> **Goal:** Create a place in the cloud (a "workspace") where you'll run the notebooks and the chat app for the rest of this project.

**What you'll do here:**
1. Create a Vayu AI Studio workspace (with Docker enabled)
2. Clone this `ask-it` repository into it
3. Install the Python dependencies
4. Pick the right kernel for the notebooks

You only do this step once.

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
3. **Add an object storage host alias:** during creation, add a **host alias** using the **IP** and **endpoint** from your SOP document. Enter the endpoint as the hostname **only** — no `http://` or `https://`.
4. **Turn on "Enable Docker in the Workspace"** before you finish. This is required later for [Step 5](../05_build_app/) and [Step 6](../06_deploy/).

</details>

---

<details>
<summary><h3>2. Get the code into your workspace</h3></summary>

Open the workspace terminal and clone this repository:

```bash
git clone https://ailab.cloudservices.tatacommunications.com/code/vayu-hackathon/ask-it.git
```

(Or upload the folder manually through the UI.)

</details>

---

<details>
<summary><h3>3. Install dependencies</h3></summary>

Still in the terminal, set up a Python virtual environment and install the packages:

```bash
python3 -m venv .venv
source .venv/bin/activate
cd ask-it
pip install -r requirements.txt

cp .env.example .env
# You'll fill in .env with credentials as you complete Steps 2–3 (and Step 6)
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

<table width="100%" style="width:100%">
<tr>
<td align="left"><a href="../README.md">Previous — Ask-It overview</a></td>
<td align="center"><a href="../README.md">Overview</a></td>
<td align="right"><a href="../01_dataset/">Next — Step 1 — Object Storage</a></td>
</tr>
</table>
