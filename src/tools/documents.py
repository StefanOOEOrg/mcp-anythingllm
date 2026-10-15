"""Document tools: list, read, replace and remove whole documents of the knowledge base.

A document is addressed by its source path (e.g. 'Travel/train-log.md'), its title or its
storage name, as rag_documents shows them. The source is stable: rag_update keeps it, and
rag_add stores it from `path`.
"""
import json
from collections import Counter
from pathlib import Path
from typing import Annotated

from pydantic import Field

import config
from client import AnythingLLMError
from tools.rag import Workspace, client, rag_tool, slugs, source_path

# More documents than this are summarised per folder instead (the list would flood the context).
MAX_LISTED = 60

Document = Annotated[str, Field(description=(
    "The document: its source path (e.g. 'Travel/train-log.md', a trailing part is enough), "
    "its title or its storage name, as rag_documents shows them."))]


def _all_documents(workspace: str | None = None) -> dict[str, dict]:
    """Storage name → document, with the slugs of every workspace that contains it."""
    found: dict[str, dict] = {}
    for slug in slugs(workspace):
        for doc in client().documents(slug):
            entry = found.setdefault(doc["name"], {**doc, "path": source_path(doc["source"]),
                                                   "workspaces": []})
            entry["workspaces"].append(slug)
    return found


def _matches(doc: dict, wanted: str) -> bool:
    """True if `wanted` names this document (storage name, source path or its end, title)."""
    path, title = doc["path"], doc["title"].lower()
    return (wanted in (doc["name"], Path(doc["name"]).name, path)
            or (bool(path) and path.endswith("/" + wanted))
            or wanted.lower() in (title, title.removesuffix(".txt")))


def resolve(document: str) -> dict:
    """The one document `document` names; a clear error for none or several."""
    wanted = source_path((document or "").strip()).lstrip("/")
    if not wanted:
        raise AnythingLLMError("Name the document (see rag_documents).")
    hits = [doc for doc in _all_documents().values() if _matches(doc, wanted)]
    if not hits:
        raise AnythingLLMError(f"No document '{document}'. rag_documents lists them.")
    if len(hits) > 1:
        names = "; ".join(doc["path"] or doc["name"] for doc in hits[:10])
        raise AnythingLLMError(f"'{document}' matches {len(hits)} documents ({names}). "
                               "Name it more precisely, e.g. by its full source path.")
    return hits[0]


def read_text(name: str) -> str:
    """The text AnythingLLM extracted from a document, read from its documents folder."""
    if not config.DOCUMENTS_DIR:
        raise AnythingLLMError("Reading documents is not configured (ANYTHINGLLM_DOCUMENTS_DIR).")
    root = Path(config.DOCUMENTS_DIR).resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise AnythingLLMError(f"Invalid document name '{name}'.")
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("pageContent") or ""
    except (OSError, ValueError) as exc:
        raise AnythingLLMError(f"Document '{name}' could not be read: {exc}") from exc


@rag_tool
def rag_documents(
    workspace: Workspace = None,
    contains: Annotated[str, Field(description="Only documents whose source or title contains "
                                               "this text, e.g. 'Todo/'. Empty = all.")] = "",
) -> dict:
    """List the documents and notes of the knowledge base (wiki): source path, title,
    workspaces, last update - e.g. all notes in a folder. Use rag_get to read one."""
    wanted = contains.strip().lower()
    docs = [{"source": doc["path"] or doc["title"], "updated": doc["updated"]}
            for doc in _all_documents(workspace).values()
            if not wanted or wanted in f"{doc['path']} {doc['title']}".lower()]
    docs.sort(key=lambda d: d["source"])
    if len(docs) <= MAX_LISTED:
        return {"documents": docs}
    folders = Counter(d["source"].rpartition("/")[0] or "(top level)" for d in docs)
    return {"folders": dict(sorted(folders.items())),
            "note": f"{len(docs)} documents - too many to list. Call rag_documents again with "
                    "contains='<folder>/' to list one folder."}


@rag_tool
def rag_get(document: Document) -> str:
    """Get (read) a whole wiki document or note - its full text, e.g. a log or plan that is to
    be updated. Returns a short header, then the complete text as plain Markdown."""
    doc = resolve(document)
    return (f"Document: {doc['path'] or doc['title']}\n"
            f"Workspaces: {', '.join(doc['workspaces'])} | updated: {doc['updated']}\n"
            "Full text follows (this is the whole document - pass it complete, edited, to "
            "rag_update):\n\n" + read_text(doc["name"]))


@rag_tool
def rag_update(
    document: Document,
    text: Annotated[str, Field(description="The COMPLETE new content (Markdown) - it replaces "
                                           "the whole document, so read it with rag_get first.")],
) -> dict:
    """Update (replace) the content of a wiki document or note; source, title and workspaces
    stay the same. Only when the user asks to change something or a skill's workflow says so."""
    if not text.strip():
        raise AnythingLLMError("The new text is empty - use rag_remove to delete a document.")
    doc = resolve(document)
    # add the new version first, so a failure never leaves the document missing
    new = client().add_text(",".join(doc["workspaces"]), doc["title"].removesuffix(".txt"),
                            text, source=doc["source"])
    if not new.get("location"):
        raise AnythingLLMError("AnythingLLM did not save the new version; nothing was changed.")
    client().remove_documents([doc["name"]])
    return {"updated": True, "source": doc["path"], "workspaces": doc["workspaces"],
            "name": new["location"]}


@rag_tool
def rag_remove(document: Document) -> dict:
    """Remove (delete) a wiki document or note for good, from every workspace and the storage.
    Only when the user explicitly asks to delete it or a skill's workflow says so."""
    doc = resolve(document)
    client().remove_documents([doc["name"]])
    return {"removed": True, "source": doc["path"], "title": doc["title"],
            "workspaces": doc["workspaces"]}
