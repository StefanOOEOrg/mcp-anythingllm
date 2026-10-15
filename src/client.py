"""Thin client for the AnythingLLM developer API (/api/v1)."""
import httpx

import config


class AnythingLLMError(Exception):
    """AnythingLLM is unreachable or refused the request (message for the agent)."""


class Client:
    """The few API calls the tools need. `transport` lets tests replace the network."""

    def __init__(self, url: str = config.URL, api_key: str = config.API_KEY,
                 timeout: float = config.TIMEOUT_SECONDS,
                 transport: httpx.BaseTransport | None = None):
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._http = httpx.Client(base_url=f"{url}/api/v1", headers=headers, timeout=timeout,
                                  transport=transport)

    def _call(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise AnythingLLMError(f"AnythingLLM is not reachable: {exc}") from exc
        if response.status_code == 403:
            raise AnythingLLMError("AnythingLLM rejected the API key (ANYTHINGLLM_API_KEY).")
        try:
            body = response.json()
        except ValueError as exc:
            raise AnythingLLMError(f"AnythingLLM answered {response.status_code} without "
                                   "JSON.") from exc
        if response.status_code >= 400 or body.get("error"):
            raise AnythingLLMError(f"AnythingLLM: {body.get('error') or response.status_code}")
        return body

    def create_workspace(self, name: str) -> dict:
        """Create a workspace; returns it with its slug."""
        return self._call("POST", "/workspace/new", json={"name": name}).get("workspace") or {}

    def workspaces(self) -> list[dict]:
        """All workspaces (name, slug, …)."""
        return self._call("GET", "/workspaces").get("workspaces") or []

    def vector_search(self, slug: str, query: str, top_n: int, threshold: float) -> list[dict]:
        """Chunks of the workspace most similar to the query: text, metadata, score."""
        body = self._call("POST", f"/workspace/{slug}/vector-search",
                          json={"query": query, "topN": top_n, "scoreThreshold": threshold})
        return body.get("results") or []

    def query(self, slug: str, question: str) -> dict:
        """Answer from the workspace's documents only (mode "query", no chat history)."""
        return self._call("POST", f"/workspace/{slug}/chat",
                          json={"message": question, "mode": "query", "reset": True})

    def add_text(self, slug: str, title: str, text: str, source: str = "") -> dict:
        """Save raw text as a document and embed it into the workspace."""
        metadata = {"title": title, **({"chunkSource": source} if source else {})}
        body = self._call("POST", "/document/raw-text",
                          json={"textContent": text, "addToWorkspaces": slug,
                                "metadata": metadata})
        docs = body.get("documents") or []
        return docs[0] if docs else {}
