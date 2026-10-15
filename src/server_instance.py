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
- rag_add(title, text, workspace): saves a note. ONLY when the user explicitly asks to store
  something.
Say which document an answer comes from. If nothing is found, say so instead of guessing.
"""

server = MCPServer(name="mcp-anythingllm", instructions=INSTRUCTIONS)
