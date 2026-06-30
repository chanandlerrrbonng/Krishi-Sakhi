# Step 0 — Vayu AI Studio Workspace

**Ask-It** › **Vayu AI Studio Workspace** · `00_vayu_workspace/`

Welcome to the **Ask-It** project! This step guides you through creating and preparing a **Vayu AI Studio** workspace for notebooks and the chat app.

---

## Quick Navigation

| | |
|:--:|:--:|
| **⬅ Previous** | [Ask-It overview](../README.md) |
| **➡ Next** | [Step 1 — Vayu Object Storage →](../01_dataset/) |

---

## Workspace Overview

![Vayu AI Studio Workspace Overview](../assets/workspaces.png)

---

## Open Workspace

Go to [Vayu AI Studio Workspace](https://ipcloud.tatacommunications.com/aistudio/#/build/workspace-list).

For the full create wizard (Start → Infrastructure → Configure Compute and Storage → Observability → Review), see the [Creating Workspace guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/workspace/#creating-workspace).

---

## Get Started

1. **Create a Vayu AI Studio workspace**

   - Log in to [Vayu AI Studio](https://ipcloud.tatacommunications.com/aistudio/#/build/workspace-list).
   - Click **Create Workspace** and follow the prompts. See the [Creating Workspace guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/workspace/#creating-workspace) for step-by-step wizard details.
   - Make sure **Enable Docker in the Workspace** is turned on before you finish creating the workspace (required for [Step 5](../05_build_app/) and [Step 6](../06_deploy/)).

2. **Import this repository**

   Clone or upload the `ask-it` repository into your new workspace:

   ```bash
   git clone https://github.com/your-org/ask-it.git
   ```

   Or upload it manually via the UI.

3. **Install Python dependencies**

   Inside your workspace terminal:

   ```bash
   cd ask-it
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

   cp .env.example .env
   # Edit .env with credentials from Steps 2–3
   ```

4. **Select the notebook kernel**

   When you open any `.ipynb` in this project, use the virtual environment above:

   1. Open **Select Kernel** and choose **Python Environments**.

   ![Select Kernel — Python Environments](../assets/kernel_select.png)

   2. Under **Select a Python Environment**, pick the **Recommended** environment (it should point to the `.venv` Python you just created).

   ![Select a Python Environment](../assets/Select_kernerl_env.png)

5. **Where to work**

   Use this workspace when working on:

   - [01_dataset/ — Vayu Object Storage](../01_dataset/)
   - [04_starter_kit/qna.ipynb — Vayu RAG ingest](../04_starter_kit/qna.ipynb)
   - [05_build_app/ — Vayu chat & deploy](../05_build_app/)

---

## Resources

| Resource | Link |
|----------|------|
| Vayu AI Studio | [Workspace Dashboard](https://ipcloud.tatacommunications.com/aistudio/#/build/workspace-list) |
| Documentation | [Workspace documentation](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/workspace/) |

---

## Navigation

| | |
|:--:|:--:|
| **⬅ Previous** | [Ask-It overview](../README.md) |
| **➡ Next** | [Step 1 — Vayu Object Storage →](../01_dataset/) |
| **Overview** | [Ask-It overview](../README.md) |
