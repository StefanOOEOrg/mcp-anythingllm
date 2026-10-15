"""A fake AnythingLLM API (httpx.MockTransport) with two workspaces and their documents."""
import itertools
import json

import httpx
import pytest

import config
from client import Client
from tools import rag

WORKSPACES = [{"name": "Personal", "slug": "personal"},
              {"name": "Work", "slug": "work"}]
HEADER = "<document_metadata>\nsourceDocument: x\n</document_metadata>\n\n"  # as in 1.17
HITS = {
    "personal": [{"text": HEADER + "Tyre pressure front 6.5 bar", "score": 0.71,
                     "metadata": {"title": "Bike.md", "chunkSource": "bike"}}],
    "work": [{"text": "Route planning in the project", "score": 0.52,
                     "metadata": {"title": "Project.md"}}],
}


# storage name → (workspaces, title, source, text); raw-text adds, remove-documents deletes
DOCUMENTS = {
    "custom-documents/raw-bike-1.json": (["personal"], "bike.txt", "wiki:Notes/Sport/Bike.md",
                                         "Tyre pressure front 6.5 bar"),
    "custom-documents/raw-train-log-1.json": (["personal"], "train-log.txt",
                                              "note:Travel/train-log.md", "2026: Linz-Wien"),
    "custom-documents/raw-project-1.json": (["work"], "project.txt", "wiki:Work/Project.md",
                                            "Route planning"),
}


class FakeApi:
    """Records the requests; answers like AnythingLLM 1.17. Documents live in `docs` and as
    JSON files in `folder` (AnythingLLM's documents folder)."""

    def __init__(self, folder=None):
        self.requests: list[tuple[str, str, dict]] = []
        self.folder = folder
        self.docs: dict[str, tuple] = {}
        self._ids = itertools.count(2)
        for name, doc in DOCUMENTS.items():
            self.store(name, *doc)

    def store(self, name, workspaces, title, source, text):
        """Keep a document (and its JSON file, if there is a folder)."""
        self.docs[name] = (workspaces, title, source, text)
        if self.folder:
            path = self.folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"title": title, "chunkSource": source,
                                        "pageContent": text}), encoding="utf-8")

    def workspace(self, slug):
        """GET /workspace/{slug}: metadata is a JSON string, as in 1.17."""
        docs = [{"docpath": name, "filename": name.split("/")[-1], "lastUpdatedAt": "2026-10-15",
                 "metadata": json.dumps({"title": title, "chunkSource": source})}
                for name, (spaces, title, source, _) in self.docs.items() if slug in spaces]
        return {"workspace": [{"slug": slug, "documents": docs}]}

    def raw_text(self, body):
        """POST /document/raw-text: AnythingLLM slugifies the title."""
        title = body["metadata"]["title"].lower().replace("/", "-").replace(" ", "-") + ".txt"
        name = f"custom-documents/raw-{title[:-4]}-{next(self._ids)}.json"
        self.store(name, body["addToWorkspaces"].split(","), title,
                   body["metadata"].get("chunkSource", ""), body["textContent"])
        return {"success": True, "error": None,
                "documents": [{"title": title, "location": name}]}

    def __call__(self, request: httpx.Request) -> httpx.Response:  # pylint: disable=too-many-return-statements
        body = json.loads(request.content) if request.content else {}
        path = request.url.path.removeprefix("/api/v1")
        self.requests.append((request.method, path, body))
        if request.headers.get("authorization") != "Bearer test-key":
            return httpx.Response(403, json={"error": "No valid api key found."})
        if path == "/workspaces":
            return httpx.Response(200, json={"workspaces": WORKSPACES})
        if path.endswith("/vector-search"):
            slug = path.split("/")[2]
            hits = [h for h in HITS.get(slug, []) if h["score"] >= body["scoreThreshold"]
                    and any(w.lower() in h["text"].lower() for w in body["query"].split())]
            return httpx.Response(200, json={"results": hits})
        if path.endswith("/chat"):
            answer = "<think>Context …\n</think>\n\nFront 6.5 bar."
            return httpx.Response(200, json={"textResponse": answer, "error": None,
                                             "sources": [{"title": "Bike.md"},
                                                         {"title": "Bike.md"}]})
        if path == "/document/raw-text":
            return httpx.Response(200, json=self.raw_text(body))
        if path.startswith("/workspace/") and request.method == "GET":
            return httpx.Response(200, json=self.workspace(path.split("/")[2]))
        if path == "/system/remove-documents":
            for name in body["names"]:
                self.docs.pop(name, None)
            return httpx.Response(200, text="OK")
        return httpx.Response(404, json={"error": "not found"})


@pytest.fixture(name="api")
def fixture_api(monkeypatch, tmp_path) -> FakeApi:
    """The fake API, wired into the tools' shared client; documents folder in tmp_path."""
    api = FakeApi(tmp_path)
    monkeypatch.setattr(config, "DOCUMENTS_DIR", str(tmp_path))
    fake = Client(url="http://test", api_key="test-key", transport=httpx.MockTransport(api))
    monkeypatch.setattr(rag, "_CLIENT", [fake])
    return api
