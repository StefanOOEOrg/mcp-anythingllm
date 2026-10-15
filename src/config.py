"""Central configuration for the mcp-anythingllm project.

Environment variables are read once here so the rest of the codebase can rely
on validated, well-known settings instead of scattering os.getenv() calls
across modules.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# === LOGGING ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# === ANYTHINGLLM ===
# Base URL of the AnythingLLM instance (e.g. a container on the harness server, loopback only)
# and an API key from Settings → Developer API. Kept in the .env next to the release.
URL = os.getenv("ANYTHINGLLM_URL", "http://127.0.0.1:3001").rstrip("/")
API_KEY = os.getenv("ANYTHINGLLM_API_KEY", "")
TIMEOUT_SECONDS = float(os.getenv("ANYTHINGLLM_TIMEOUT_SECONDS", "180"))

# === RETRIEVAL ===
# Hits below this similarity (0..1) are dropped. BGE-M3 scores unrelated text at
# ~0.4-0.53 and matches at ~0.6-0.75.
SCORE_THRESHOLD = float(os.getenv("ANYTHINGLLM_SCORE_THRESHOLD", "0.5"))
TOP_N = int(os.getenv("ANYTHINGLLM_TOP_N", "6"))

# === DOCUMENTS ===
# AnythingLLM's documents folder (storage/documents, the parsed text as JSON), readable by this
# server. The API returns no document text, so rag_get reads it here; empty = rag_get disabled.
DOCUMENTS_DIR = os.getenv("ANYTHINGLLM_DOCUMENTS_DIR", "")
