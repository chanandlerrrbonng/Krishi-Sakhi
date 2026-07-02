"""Download tcl-cosign tooling and sign or verify a container image.

Run from the repo root after building and pushing an image. Set registry credentials in `.env` (see `.env.example`); export `IMAGE` for the image to sign:

    export IMAGE=$IMAGE_REGISTRY/$REGISTRY_PROJECT/ask-it-chat:latest
    python 06_deploy/image-signing/sign_image.py sign

To verify:

    export IMAGE=$IMAGE_REGISTRY/$REGISTRY_PROJECT/ask-it-chat:latest
    python 06_deploy/image-signing/sign_image.py verify

See `06_deploy/image-signing/README.md` and the Container Registry guide for full details.
"""

import os
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

SIGN_DIR = Path(__file__).resolve().parent
REPO_ROOT = SIGN_DIR.parent.parent
load_dotenv(REPO_ROOT / ".env")
COSIGN_BIN = REPO_ROOT / "tcl-cosign"
COSIGN_URL = "https://ipcloud.tatacommunications.com/docs/downloads/tcl-cosign"

FULCIO_URL = "https://ipcloud.tatacommunications.com/iks-fulcio/api/v1/rootCert"
REKOR_URL = "https://ipcloud.tatacommunications.com/iks-rekor/api/v1/log/publicKey"
REKOR_SERVICE = "https://ipcloud.tatacommunications.com/iks-rekor"
OIDC_ISSUER = "https://ipcloud.tatacommunications.com/iks-auth/realms/idp"
FULCIO_SERVICE = "https://ipcloud.tatacommunications.com/iks-fulcio"

CTLOG_KEY = """-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEUuv1YKkGK0uYY1Y9KbKfQNBYl8iI
bY+CTnvZFUm07RvwR8wMBZle7pkNdw6hGbxzNqYUYvMKkYmcBQ4hQQ7+Gg==
-----END PUBLIC KEY-----
"""


def normalize_image_ref(value: str) -> str:
    value = value.strip()
    lower = value.lower()
    for prefix in ("https://", "http://"):
        if lower.startswith(prefix):
            value = value[len(prefix) :]
            break
    return value.rstrip("/")


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        print(f"Error: export {name} before running this script.", file=sys.stderr)
        sys.exit(1)
    return value


def download_file(url: str, dest: Path) -> None:
    print(f"Downloading {url} → {dest}")
    urllib.request.urlretrieve(url, dest)


def setup_signing_assets() -> dict[str, str]:
    SIGN_DIR.mkdir(parents=True, exist_ok=True)

    if not COSIGN_BIN.is_file():
        download_file(COSIGN_URL, COSIGN_BIN)
        COSIGN_BIN.chmod(COSIGN_BIN.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"Installed {COSIGN_BIN} (executable)")
    else:
        print(f"Using existing {COSIGN_BIN}")

    fulcio = SIGN_DIR / "fulcio.crt"
    rekor = SIGN_DIR / "rekor.key"
    ctlog = SIGN_DIR / "ctlog.key"

    download_file(FULCIO_URL, fulcio)
    download_file(REKOR_URL, rekor)
    ctlog.write_text(CTLOG_KEY)

    env = os.environ.copy()
    env["SIGSTORE_REKOR_PUBLIC_KEY"] = str(rekor)
    env["SIGSTORE_ROOT_FILE"] = str(fulcio)
    env["SIGSTORE_CT_LOG_PUBLIC_KEY_FILE"] = str(ctlog)
    return env


def sign_image() -> None:
    image = normalize_image_ref(require_env("IMAGE"))
    username = require_env("REGISTRY_USERNAME")
    password = require_env("REGISTRY_PASSWORD")
    env = setup_signing_assets()

    cmd = [
        str(COSIGN_BIN),
        "sign",
        image,
        f"--rekor-url={REKOR_SERVICE}",
        f"--oidc-issuer={OIDC_ISSUER}",
        "--oidc-client-id=iks",
        f"--fulcio-url={FULCIO_SERVICE}",
        f"--registry-username={username}",
        f"--registry-password={password}",
        "--recursive"
    ]
    print("Signing image (follow the browser prompt if shown)...")
    subprocess.run(cmd, env=env, check=True)
    print(f"DONE: signed {image}")


def verify_image() -> None:
    image = normalize_image_ref(require_env("IMAGE"))
    username = require_env("REGISTRY_USERNAME")
    password = require_env("REGISTRY_PASSWORD")
    vayu_username = require_env("VAYU_USERNAME")
    env = setup_signing_assets()

    cmd = [
        str(COSIGN_BIN),
        "verify",
        image,
        f"--rekor-url={REKOR_SERVICE}",
        f"--certificate-identity={vayu_username}",
        f"--certificate-oidc-issuer={OIDC_ISSUER}",
        f"--registry-username={username}",
        f"--registry-password={password}",
    ]
    print(f"Verifying signature for {image}...")
    subprocess.run(cmd, env=env, check=True)
    print(f"DONE: verified {image}")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"sign", "verify"}:
        print("Usage: python 06_deploy/image-signing/sign_image.py sign|verify", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "sign":
        sign_image()
    else:
        verify_image()


if __name__ == "__main__":
    main()
