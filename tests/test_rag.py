"""The knowledge-base tools against the fake AnythingLLM API."""
import httpx
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from client import AnythingLLMError, Client
from tools.rag import rag_add, rag_answer, rag_search, rag_workspaces


def test_workspaces_lists_name_and_slug(api):
    """rag_workspaces returns name and slug of every workspace."""
    assert rag_workspaces() == [{"name": "Personal", "slug": "personal"},
                                {"name": "Work", "slug": "work"}]
    assert api.requests[0][:2] == ("GET", "/workspaces")


def test_search_merges_all_workspaces_by_score(api):
    """Without a workspace every workspace is searched; hits are merged by score."""
    hits = rag_search("pressure planning")["hits"]
    assert [(h["workspace"], h["title"], h["score"]) for h in hits] == [
        ("personal", "Bike.md", 0.71), ("work", "Project.md", 0.52)]
    assert hits[0]["source"] == "bike"
    assert hits[0]["text"] == "Tyre pressure front 6.5 bar"
    search = [r for r in api.requests if r[1].endswith("/vector-search")]
    assert len(search) == 2 and search[0][2]["topN"] == 6


def test_search_in_one_workspace_by_name_and_unknown_workspace(api):
    """A workspace can be named by its display name; an unknown one lists the valid slugs."""
    hits = rag_search("pressure planning", workspace="Work")["hits"]
    assert [h["workspace"] for h in hits] == ["work"]
    with pytest.raises(ToolError, match="no workspace 'Cooking'.*personal, work"):
        rag_search("x", workspace="Cooking")
    assert api.requests


def test_search_without_hits_says_so(api):
    """No hits → an empty list and a note for the agent."""
    assert rag_search("quantum physics") == {
        "hits": [], "note": "Nothing in the knowledge base matches this query."}
    assert api.requests


def test_answer_uses_best_workspace_query_mode_and_dedups_sources(api):
    """The best-scoring workspace answers in query mode; duplicate sources are dropped."""
    result = rag_answer("tyre pressure front?")
    assert result == {"workspace": "personal", "answer": "Front 6.5 bar.",
                      "sources": ["Bike.md"]}
    method, path, body = api.requests[-1]
    assert (method, path) == ("POST", "/workspace/personal/chat")
    assert body["mode"] == "query" and body["reset"] is True


def test_answer_without_matching_documents_skips_the_llm(api):
    """Nothing found → no chat call, answer None."""
    assert rag_answer("quantum physics")["answer"] is None
    assert not [r for r in api.requests if r[1].endswith("/chat")]


def test_add_needs_workspace_and_embeds_into_it(api):
    """rag_add refuses without workspace and embeds into the named one."""
    with pytest.raises(ToolError, match="needs a workspace"):
        rag_add("Note", "text", "")
    assert rag_add("Note", "text", "personal") == {
        "saved": True, "workspace": "personal", "title": "Note",
        "location": "custom-documents/raw-x.json"}
    assert api.requests[-1][2]["addToWorkspaces"] == "personal"


def test_wrong_key_and_unreachable_server_become_clear_errors(api):
    """403 and connection errors become readable AnythingLLMErrors."""
    bad = Client(url="http://test", api_key="wrong", transport=httpx.MockTransport(api))
    with pytest.raises(AnythingLLMError, match="rejected the API key"):
        bad.workspaces()

    def refuse(request):
        raise httpx.ConnectError("connection refused", request=request)
    down = Client(url="http://test", api_key="test-key", transport=httpx.MockTransport(refuse))
    with pytest.raises(AnythingLLMError, match="not reachable"):
        down.workspaces()
