# Image signing (optional automation)

**Ask-It** › [Step 6 — Deploy](../README.md) › `06_deploy/image-signing/`

> **Goal:** Sign your pushed Docker image the easy way, using the helper script [`sign_image.py`](sign_image.py), instead of the manual signing steps.

Vayu ML Services only run **signed** container images. Use this if you'd rather automate signing than follow the manual steps in the [Container Registry guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/registry/).

---

## What the script creates

Running [`sign_image.py`](sign_image.py) downloads the signing tools and writes these files:

| Path | Purpose |
|------|---------|
| `ask-it/tcl-cosign` | The `tcl-cosign` binary (repo root, made executable) |
| `06_deploy/image-signing/fulcio.crt` | Sigstore root certificate |
| `06_deploy/image-signing/rekor.key` | Rekor public key |
| `06_deploy/image-signing/ctlog.key` | CT log public key |

> These certificate files are gitignored and re-downloaded each time you run the script — you don't need to manage them yourself.

---

## Before you start

Make sure these are set in the root [`.env`](../../.env.example):

- `IMAGE_REGISTRY`
- `REGISTRY_PROJECT`
- `REGISTRY_USERNAME`
- `REGISTRY_PASSWORD`
- `VAYU_USERNAME` (needed for verify only)

You should also have already built and pushed the image in [Step 6 → Step 1](../README.md#step-1--build-and-push-the-docker-image).

---

## Sign the image

```bash
cd ask-it
set -a && source .env && set +a

export IMAGE=$IMAGE_REGISTRY/$REGISTRY_PROJECT/ask-it-chat:latest

python 06_deploy/image-signing/sign_image.py sign
```

> During signing, a browser prompt appears — follow it and copy the authorization code when redirected.

---

## Verify (optional)

```bash
export IMAGE=$IMAGE_REGISTRY/$REGISTRY_PROJECT/ask-it-chat:latest
python 06_deploy/image-signing/sign_image.py verify
```

---

## ✅ You're done when

- `sign` completes without errors.
- (Optional) `verify` confirms the signature for your image.

---

## Environment variables

| Variable | Used for | Source |
|----------|----------|--------|
| `IMAGE_REGISTRY` | build + sign + verify | Root `.env` — registry host from your Vayu profile |
| `REGISTRY_PROJECT` | build + sign + verify | Root `.env` — registry project name (between host and image repo) |
| `IMAGE` | sign + verify | Export per run: `$IMAGE_REGISTRY/$REGISTRY_PROJECT/ask-it-chat:latest` |
| `REGISTRY_USERNAME` | sign + verify + `docker login` | Root `.env` — container registry username |
| `REGISTRY_PASSWORD` | sign + verify + `docker login` | Root `.env` — container registry CLI secret |
| `VAYU_USERNAME` | verify only | Root `.env` — your Vayu username (certificate identity) |

---

## Navigation

| | |
|:--|--:|
| [← Back to Step 6 — Deploy](../README.md) | [Manual signing guide →](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/registry/) |
