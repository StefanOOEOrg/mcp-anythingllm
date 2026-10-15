"""A fake AnythingLLM API (httpx.MockTransport) with two workspaces."""
import json

import httpx
import pytest

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


class FakeApi:
    """Records the requests; answers like AnythingLLM 1.17."""

    def __init__(self):
        self.requests: list[tuple[str, str, dict]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
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
            return httpx.Response(200, json={"success": True, "error": None, "documents": [
                {"title": body["metadata"]["title"], "location": "custom-documents/raw-x.json"}]})
        return httpx.Response(404, json={"error": "not found"})


@pytest.fixture(name="api")
def fixture_api(monkeypatch) -> FakeApi:
    """The fake API, wired into the tools' shared client."""
    api = FakeApi()
    fake = Client(url="http://test", api_key="test-key", transport=httpx.MockTransport(api))
    monkeypatch.setattr(rag, "_CLIENT", [fake])
    return api
