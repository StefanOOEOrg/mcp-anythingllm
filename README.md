# mcp-anythingllm

[![CI](https://github.com/StefanOOEOrg/mcp-anythingllm/actions/workflows/ci.yml/badge.svg)](https://github.com/StefanOOEOrg/mcp-anythingllm/actions/workflows/ci.yml)

MCP server (stdio) that gives Hermes access to the knowledge base in
[AnythingLLM](https://github.com/Mintplex-Labs/anything-llm): documents uploaded through the
AnythingLLM web UI (PDF, Word, web pages, Markdown …), organised in workspaces.

Typical setup: AnythingLLM runs as a container on the harness server (loopback port 3001), LLM
and embedding model come from an OpenAI-compatible LLM server. This MCP server only talks to
AnythingLLM's developer API.

## Requirements

- **Python 3.11 or newer** — the pinned dependencies require it (`rpds-py`, `PyJWT`); the CI runs
  3.11 and 3.14.
- A running **AnythingLLM** instance with the Developer API enabled (Settings → Developer API gives
  the key). The server talks to it over HTTP, nothing else.
- Optional: read access to AnythingLLM's `storage/documents` folder — only needed for `rag_get`.

## Installation

```bash
git clone https://github.com/StefanOOEOrg/mcp-anythingllm.git
cd mcp-anythingllm
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp .env.example .env        # set ANYTHINGLLM_URL and ANYTHINGLLM_API_KEY
```

Then register it in your MCP client (see [Hermes](#hermes) for the profile entry).

## Tools

| Tool | What it does |
|---|---|
| `rag_workspaces()` | Lists the workspaces (name, slug). |
| `rag_search(query, workspace?)` | Best passages (text, document title, workspace, score 0..1); all workspaces when `workspace` is empty. |
| `rag_answer(question, workspace?)` | Answer from the documents only (chat mode `query`), with sources. Without `workspace` the workspace with the best passage answers; if nothing matches, no LLM call. |
| `rag_documents(workspace?, contains?)` | Lists the documents: source path, title, workspaces, last update. |
| `rag_get(document)` | The whole text of one document (needs `ANYTHINGLLM_DOCUMENTS_DIR`). |
| `rag_add(title, text, workspace, path?)` | Saves a new note and embeds it; `path` gives it a stable source to find it again. |
| `rag_edit(document, old_text, new_text)` | Replaces one passage that occurs exactly once (e.g. ticks off a line); only the change is sent, the document is then stored like `rag_update`. |
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
| `LOG_LEVEL` | `INFO` | log level of the server (`DEBUG`, `INFO`, `WARNING`, …) |

## Project structure

```
mcp-anythingllm/
├── src/
│   ├── client.py            # AnythingLLM developer API (search, documents, workspaces)
│   ├── config.py            # ANYTHINGLLM_* / LOG_LEVEL from the environment
│   ├── main.py              # entry point (starts the server over stdio)
│   ├── mcp_server.py        # composition root: server + tools
│   ├── server_instance.py   # the shared MCP server instance
│   └── tools/
│       ├── documents.py     # rag_documents / rag_get / rag_add / rag_edit / rag_update / rag_remove
│       └── rag.py           # rag_workspaces / rag_search / rag_answer
├── tests/                   # fake API via httpx.MockTransport, no network
├── scripts/import_wiki.py   # bulk import of a Markdown folder
├── .github/workflows/ci.yml # pytest + pylint on 3.11 and 3.14
├── .env.example             # copy to .env
├── .pylintrc
├── pytest.ini
├── requirements.txt / requirements-dev.txt
├── LICENSE
└── README.md
```

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

## Scope / Limitations

- A single-user tool, not a service: it runs locally over stdio — no port of its own, no
  authentication, no multi-user support.
- It needs a running AnythingLLM instance plus its Developer API key; without them every tool fails
  with a readable message.
- The API key is stored in plain text in `.env` — keep that file out of the repo and out of logs.
- Several tools **write** to the knowledge base (`rag_add`, `rag_edit`, `rag_update`, `rag_remove`);
  they are meant for explicit requests, not for background use.
- `rag_get` needs a readable `ANYTHINGLLM_DOCUMENTS_DIR`; the API itself returns no document text.
- Answers come from your own LLM server through AnythingLLM, so quality and latency depend on that
  setup — and the API is not part of AnythingLLM's public contract, so it can change between versions.

## License

[MIT](LICENSE)
