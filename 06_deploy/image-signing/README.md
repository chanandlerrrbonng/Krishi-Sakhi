# Image signing (optional automation)

**Ask-It** › **Step 6** › `06_deploy/image-signing/`

Use this guide if you prefer the automated signing flow with [`sign_image.py`](sign_image.py) instead of following the manual steps in the [Container Registry guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/registry/).

Vayu ML Services require **signed** container images. Sign the chat image after push.

---

## What gets created

[`sign_image.py`](sign_image.py) downloads tooling and writes signing assets in this folder:

| Path | Purpose |
|------|---------|
| `ask-it/tcl-cosign` | `tcl-cosign` binary (repo root, made executable) |
| `06_deploy/image-signing/fulcio.crt` | Sigstore root certificate |
| `06_deploy/image-signing/rekor.key` | Rekor public key |
| `06_deploy/image-signing/ctlog.key` | CT log public key |

These certificate files are gitignored and re-downloaded when you run the script.

---

## Prerequisites

Set registry variables in the root [`.env`](../../README.md) (see [`.env.example`](../../.env.example)):

- `IMAGE_REGISTRY`
- `REGISTRY_PROJECT`
- `REGISTRY_USERNAME`
- `REGISTRY_PASSWORD`
- `VAYU_USERNAME` (verify only)

---

## Sign the chat image

```bash
cd ask-it
set -a && source .env && set +a

export IMAGE=$IMAGE_REGISTRY/$REGISTRY_PROJECT/ask-it-chat:latest

python 06_deploy/image-signing/sign_image.py sign
```

Follow the browser prompt during signing (copy the authorization code when redirected).

---

## Verify (optional)

```bash
export IMAGE=$IMAGE_REGISTRY/$REGISTRY_PROJECT/ask-it-chat:latest
python 06_deploy/image-signing/sign_image.py verify
```

---

## Environment variables

| Variable | Used for | Source |
|----------|----------|--------|
| `IMAGE_REGISTRY` | build + sign + verify | Root `.env` — registry host from your Vayu user profile |
| `REGISTRY_PROJECT` | build + sign + verify | Root `.env` — registry project name (between host and image repo) |
| `IMAGE` | sign + verify | Export per run: `$IMAGE_REGISTRY/$REGISTRY_PROJECT/ask-it-chat:latest` |
| `REGISTRY_USERNAME` | sign + verify + `docker login` | Root `.env` — container registry username |
| `REGISTRY_PASSWORD` | sign + verify + `docker login` | Root `.env` — container registry CLI secret |
| `VAYU_USERNAME` | verify only | Root `.env` — your Vayu username (certificate identity) |

---

## Navigation

| | |
|---|---|
| **Back** | [Step 6 — Deploy](../README.md) |
| **Manual signing** | [Container Registry guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/registry/) |
