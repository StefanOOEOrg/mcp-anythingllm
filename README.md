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
| `rag_add(title, text, workspace)` | Saves a note as a document and embeds it — only on the user's explicit request. |

## Configuration (`.env`)

| Variable | Default | |
|---|---|---|
| `ANYTHINGLLM_URL` | `http://127.0.0.1:3001` | AnythingLLM instance |
| `ANYTHINGLLM_API_KEY` | — | Settings → Developer API |
| `ANYTHINGLLM_TIMEOUT_SECONDS` | `180` | per request (answers come from the local LLM) |
| `ANYTHINGLLM_SCORE_THRESHOLD` | `0.5` | minimum similarity of a passage (unrelated ≈ 0.4–0.53, matches ≈ 0.6–0.75) |
| `ANYTHINGLLM_TOP_N` | `6` | passages per search |

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
