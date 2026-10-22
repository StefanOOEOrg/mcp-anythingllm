"""Shared MCPServer instance that tool modules register themselves against."""
from mcp.server.mcpserver import MCPServer

INSTRUCTIONS = """\
The user's personal knowledge base (AnythingLLM): their own notes, documents, projects, setups,
preferences and numbers, organised in workspaces (rag_workspaces lists them). For any question
about the user's own domains, look here BEFORE web search or memory - this is the authoritative
source; web results are only a fallback.

- rag_answer(question): an answer written from the matching documents, with its sources.
  Without `workspace` the best matching workspace is chosen automatically.
- rag_search(query): the raw passages with source and score, to read or quote yourself.
- rag_documents(workspace?, contains?): lists the documents (source path, title); rag_get(document)
  reads a whole one.
- rag_add(title, text, workspace, path?), rag_edit(document, old_text, new_text),
  rag_update(document, text), rag_remove(document): write. ONLY when the user asks to store,
  change or delete something, or a skill's workflow says so.
  For a small change use rag_edit: it replaces one passage copied exactly from rag_get.
  rag_update replaces the whole document: read it with rag_get first, pass the complete text.
  If a skill covers this kind of note (todos, ideas, logs, ...), load it BEFORE writing: it
  defines the path, and an existing log is updated (rag_edit/rag_update), never added a second time.
- Listing a folder (e.g. all open todos) is rag_documents(contains='<folder>/'), not rag_search -
  a search only returns the few best matching passages.
Say which document an answer comes from. If nothing is found, say so instead of guessing.
Messages may already carry passages from this knowledge base, inserted automatically before
the turn. If they answer the question, use them directly instead of searching again.
"""

server = MCPServer(name="mcp-anythingllm", instructions=INSTRUCTIONS)
