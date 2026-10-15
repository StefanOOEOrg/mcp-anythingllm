"""Knowledge-base tools: search, answer and add documents in AnythingLLM workspaces."""
import functools
import re
from typing import Annotated, Callable

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

import config
from client import AnythingLLMError, Client
from server_instance import server

# Replaced in tests; created on first use so importing the module needs no configuration.
_CLIENT: list[Client] = []

# AnythingLLM wraps the model's reasoning in <think>…</think> inside the answer text.
_THINK = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
# … and prefixes every chunk with a metadata header.
_METADATA = re.compile(r"<document_metadata>.*?</document_metadata>\s*", re.DOTALL)

Workspace = Annotated[str | None, Field(description=(
    "Workspace name or slug as rag_workspaces shows it, e.g. 'personlich'. Leave empty to "
    "search all workspaces."))]


def client() -> Client:
    """The shared API client."""
    if not _CLIENT:
        _CLIENT.append(Client())
    return _CLIENT[0]


def rag_tool(func: Callable) -> Callable:
    """Register func as an MCP tool; AnythingLLMError reaches the agent as ToolError."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AnythingLLMError as exc:
            raise ToolError(str(exc)) from exc
    server.tool()(wrapper)
    return wrapper


def slugs(workspace: str | None) -> list[str]:
    """The slugs to search: the one named (by name or slug) or all of them."""
    spaces = client().workspaces()
    if not workspace:
        return [space["slug"] for space in spaces]
    wanted = workspace.strip().lower()
    for space in spaces:
        if wanted in (space["slug"].lower(), str(space.get("name", "")).lower()):
            return [space["slug"]]
    names = ", ".join(space["slug"] for space in spaces) or "none"
    raise AnythingLLMError(f"There is no workspace '{workspace}'. Workspaces: {names}.")


def search(query: str, workspace: str | None = None, top_n: int = config.TOP_N) -> list[dict]:
    """Best passages over the given workspace(s), highest score first."""
    hits = []
    for slug in slugs(workspace):
        for hit in client().vector_search(slug, query, top_n, config.SCORE_THRESHOLD):
            meta = hit.get("metadata") or {}
            hits.append({"workspace": slug, "title": meta.get("title") or "?",
                         "source": meta.get("chunkSource") or meta.get("url") or "",
                         "score": round(float(hit.get("score") or 0), 3),
                         "text": _METADATA.sub("", hit.get("text") or "").strip()})
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:top_n]


@rag_tool
def rag_workspaces() -> list[dict]:
    """List the workspaces of the knowledge base (wiki): name and slug."""
    return [{"name": space.get("name"), "slug": space["slug"]}
            for space in client().workspaces()]


@rag_tool
def rag_search(
    query: Annotated[str, Field(description="What to look for, as a question or keywords, "
                                            "e.g. 'tyre pressure road bike'.")],
    workspace: Workspace = None,
) -> dict:
    """Search the user's knowledge base (wiki, notes, documents): the passages that match the
    query (text, document title, workspace, similarity score 0..1). Use it to read the sources
    yourself."""
    hits = search(query, workspace)
    if not hits:
        return {"hits": [], "note": "Nothing in the knowledge base matches this query."}
    return {"hits": hits}


@rag_tool
def rag_answer(
    question: Annotated[str, Field(description="The user's question in their words.")],
    workspace: Workspace = None,
) -> dict:
    """Answer a question from the user's knowledge base (wiki, notes, documents) only, with the
    documents used as sources.
    Without `workspace`, the workspace with the best matching passage is used."""
    best = search(question, workspace, top_n=1)
    if not best:
        return {"answer": None,
                "note": "Nothing in the knowledge base matches this question - say so."}
    slug = best[0]["workspace"]
    body = client().query(slug, question)
    sources = []
    for source in body.get("sources") or []:
        if source.get("title") and source["title"] not in sources:
            sources.append(source["title"])
    answer = _THINK.sub("", body.get("textResponse") or "").strip()
    if not answer or answer == "null":
        raise AnythingLLMError("The model returned no answer (reasoning used up the token "
                               "limit?). Use rag_search and answer from the passages.")
    return {"workspace": slug, "answer": answer, "sources": sources}


@rag_tool
def rag_add(
    title: Annotated[str, Field(description="Title of the note, e.g. 'Tyre pressure "
                                            "road bike'.")],
    text: Annotated[str, Field(description="The full content (Markdown).")],
    workspace: Annotated[str, Field(description="Workspace name or slug to store it in.")],
    path: Annotated[str, Field(description=(
        "Optional stable source path, e.g. 'Travel/train-log.md', to find the note again with "
        "rag_get / rag_update / rag_remove. Must not exist yet."))] = "",
) -> dict:
    """Add (save) a new note or document to the knowledge base (wiki). Only when the user asks
    to store something or a skill's workflow says so."""
    if not (workspace or "").strip():
        raise AnythingLLMError("rag_add needs a workspace (see rag_workspaces).")
    slug = slugs(workspace)[0]
    path = path.strip().lstrip("/")
    if path:
        for space in client().workspaces():
            for doc in client().documents(space["slug"]):
                if doc["source"].split(":", 1)[-1] == path:
                    raise AnythingLLMError(f"'{path}' exists already - use rag_update.")
    doc = client().add_text(slug, title, text, source=f"note:{path}" if path else "")
    return {"saved": True, "workspace": slug, "title": doc.get("title") or title,
            "source": path, "location": doc.get("location")}
