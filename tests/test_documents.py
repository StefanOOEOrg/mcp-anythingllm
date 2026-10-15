"""Document tools (list, read, replace, remove) against the fake AnythingLLM API."""
import pytest
from mcp.server.mcpserver.exceptions import ToolError

import config
from tools.documents import rag_documents, rag_get, rag_remove, rag_update


def test_documents_lists_sources_without_scheme_and_filters(api):
    """rag_documents shows source paths without 'wiki:'/'note:', sorted; `contains` filters."""
    docs = rag_documents()["documents"]
    assert [d["source"] for d in docs] == [
        "Notes/Sport/Bike.md", "Travel/train-log.md", "Work/Project.md"]
    assert docs[0]["workspaces"] == ["personal"]
    assert [d["source"] for d in rag_documents(contains="travel/")["documents"]] == [
        "Travel/train-log.md"]
    assert [d["source"] for d in rag_documents(workspace="Work")["documents"]] == [
        "Work/Project.md"]
    assert api.requests


@pytest.mark.parametrize("name", ["Travel/train-log.md", "train-log.md", "train-log",
                                  "custom-documents/raw-train-log-1.json"])
def test_get_finds_a_document_by_path_end_title_or_storage_name(api, name):
    """Source path (or its end), title and storage name all address the same document."""
    doc = rag_get(name)
    assert (doc["source"], doc["text"]) == ("Travel/train-log.md", "2026: Linz-Wien")
    assert api.requests


def test_get_errors_for_unknown_ambiguous_and_unconfigured(api, monkeypatch):
    """No match, several matches and a missing documents folder give clear errors."""
    with pytest.raises(ToolError, match="No document 'Cooking.md'"):
        rag_get("Cooking.md")
    api.store("custom-documents/raw-bike-9.json", ["work"], "bike2.txt", "wiki:Work/Bike.md", "")
    with pytest.raises(ToolError, match="matches 2 documents"):
        rag_get("Bike.md")
    monkeypatch.setattr(config, "DOCUMENTS_DIR", "")
    with pytest.raises(ToolError, match="ANYTHINGLLM_DOCUMENTS_DIR"):
        rag_get("Travel/train-log.md")


def test_update_adds_the_new_version_first_then_removes_the_old(api):
    """rag_update keeps source, title and workspaces; the old version is gone afterwards."""
    result = rag_update("train-log.md", "2026: Linz-Wien, Wels-Graz")
    assert result["updated"] and result["source"] == "Travel/train-log.md"
    methods = [(m, p) for m, p, _ in api.requests if p in ("/document/raw-text",
                                                            "/system/remove-documents")]
    assert methods == [("POST", "/document/raw-text"), ("DELETE", "/system/remove-documents")]
    assert "custom-documents/raw-train-log-1.json" not in api.docs
    assert api.docs[result["name"]][:3] == (["personal"], "train-log.txt",
                                            "note:Travel/train-log.md")
    assert rag_get("Travel/train-log.md")["text"] == "2026: Linz-Wien, Wels-Graz"
    with pytest.raises(ToolError, match="empty"):
        rag_update("train-log.md", "  ")


def test_remove_deletes_the_document(api):
    """rag_remove deletes it for good; afterwards it cannot be found."""
    assert rag_remove("Work/Project.md") == {
        "removed": True, "source": "Work/Project.md", "title": "project.txt",
        "workspaces": ["work"]}
    with pytest.raises(ToolError, match="No document"):
        rag_get("Work/Project.md")
    assert "custom-documents/raw-project-1.json" not in api.docs
