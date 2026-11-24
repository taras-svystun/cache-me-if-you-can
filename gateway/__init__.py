"""Environment defaults, set before anything imports anthropic or huggingface_hub.

huggingface_hub reads HF_HOME and HF_HUB_OFFLINE once, at import, so they must be set here,
not in load_env(). SSL_CERT_FILE: the sandbox blocks the macOS trust service that Python TLS
asks by default (journal, S0), so point TLS at certifi's bundle instead."""
import os
from pathlib import Path

import certifi

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("HF_HOME", str(ROOT / ".cache"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")  # models are on disk; no revision check per load
