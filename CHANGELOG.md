# Changelog

## 0.1.0 — 2026-10-24

Initial release.

- `rag_workspaces()`, `rag_search(query, workspace?)`, `rag_answer(question, workspace?)` — reading
  side: list workspaces, best passages with score, and answers that are grounded in the documents
  (chat mode `query`) with sources.
- `rag_documents`, `rag_get`, `rag_add`, `rag_edit`, `rag_update`, `rag_remove` — document side:
  list, read (needs `ANYTHINGLLM_DOCUMENTS_DIR`), add, replace a single passage, replace a whole
  document, delete.
- Local MCP server over stdio; talks only to the AnythingLLM developer API.
- Configuration via `.env` (`ANYTHINGLLM_URL`, `_API_KEY`, `_TIMEOUT_SECONDS`, `_SCORE_THRESHOLD`,
  `_TOP_N`, `_DOCUMENTS_DIR`, `LOG_LEVEL`); `.env.example` ships the template.
- `scripts/import_wiki.py` — bulk import of a Markdown folder into workspaces.
- CI: pytest + pylint on Python 3.11 and 3.14.
