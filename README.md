# mcp-anythingllm

MCP server (stdio) that gives Hermes access to the knowledge base in
[AnythingLLM](https://github.com/Mintplex-Labs/anything-llm): documents uploaded through the
AnythingLLM web UI (PDF, Word, web pages, Markdown …), organised in workspaces.

Typical setup: AnythingLLM runs as a container on the harness server (loopback port 3001), LLM
and embedding model come from an OpenAI-compatible LLM server. This MCP server only talks to
AnythingLLM's developer API.

## Tools

| Tool | What it does |
|---|---|
| `rag_workspaces()` | Lists the workspaces (name, slug). |
| `rag_search(query, workspace?)` | Best passages (text, document title, workspace, score 0..1); all workspaces when `workspace` is empty. |
| `rag_answer(question, workspace?)` | Answer from the documents only (chat mode `query`), with sources. Without `workspace` the workspace with the best passage answers; if nothing matches, no LLM call. |
| `rag_documents(workspace?, contains?)` | Lists the documents: source path, title, workspaces, last update. |
| `rag_get(document)` | The whole text of one document (needs `ANYTHINGLLM_DOCUMENTS_DIR`). |
| `rag_add(title, text, workspace, path?)` | Saves a new note and embeds it; `path` gives it a stable source to find it again. |
| `rag_update(document, text)` | Replaces a document's content (new version is embedded first, then the old one removed); source, title and workspaces stay. |
| `rag_remove(document)` | Deletes a document from every workspace and the storage. |

Writing tools are meant for explicit requests or a skill's workflow. A `document` is named by its
source path (or its end, e.g. `train-log.md`), its title or its storage name.

## Configuration (`.env`)

| Variable | Default | |
|---|---|---|
| `ANYTHINGLLM_URL` | `http://127.0.0.1:3001` | AnythingLLM instance |
| `ANYTHINGLLM_API_KEY` | — | Settings → Developer API |
| `ANYTHINGLLM_TIMEOUT_SECONDS` | `180` | per request (answers come from the local LLM) |
| `ANYTHINGLLM_SCORE_THRESHOLD` | `0.5` | minimum similarity of a passage (unrelated ≈ 0.4–0.53, matches ≈ 0.6–0.75) |
| `ANYTHINGLLM_TOP_N` | `6` | passages per search |
| `ANYTHINGLLM_DOCUMENTS_DIR` | — | AnythingLLM's `storage/documents` folder, readable by this server (the API returns no document text); without it `rag_get` is disabled |

## Development

```bash
python3 -m venv venv && venv/bin/pip install -r requirements-dev.txt
venv/bin/python -m pytest          # fake API via httpx.MockTransport, no network
venv/bin/pylint src tests
```

## Hermes

Install the release anywhere (with its own venv and `.env`) and add it to the profile's
`config.yaml`:

```yaml
mcp_servers:
  mcp-anythingllm:
    command: /path/to/mcp-anythingllm/.venv/bin/python
    args: [/path/to/mcp-anythingllm/src/main.py]
```

## Importing an existing Markdown folder

```bash
venv/bin/python scripts/import_wiki.py ~/notes --default Personal --folder Work=Work --dry-run
```

Files below a folder `Work` go to the workspace "Work", everything else to "Personal";
missing workspaces are created. Already imported files are skipped on a rerun.
