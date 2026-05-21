from __future__ import annotations

from types import SimpleNamespace


def _point(text: str, score: float, source_id: str = "c_00001"):
    return SimpleNamespace(
        score=score,
        payload={
            "text": text,
            "chunk_id": source_id,
            "doc_id": "doc_1",
            "section_title": "Warranty",
            "section_id": "s_001",
            "page_start": 3,
            "page_end": 4,
            "chunk_type": "text",
        },
    )


def test_retrieve_section_context_uses_query_embedding_and_preserves_contract(monkeypatch):
    from pipeline_one.retrieval import retrieve_context as module

    calls = {}

    def fake_embed_query(text: str, api_key: str):
        calls["query_text"] = text
        calls["api_key"] = api_key
        return [0.1, 0.2, 0.3]

    class FakeClient:
        def __init__(self, url: str, api_key: str):
            calls["client"] = (url, api_key)

        def query_points(self, collection_name, query, limit, query_filter):
            calls.setdefault("collections", []).append(collection_name)
            if collection_name == "tender_chunks":
                return SimpleNamespace(points=[_point("Tender warranty clause", 0.91)])
            return SimpleNamespace(points=[_point("Company warranty capability", 0.88, "c_00002")])

    monkeypatch.setattr(module, "embed_query", fake_embed_query)
    monkeypatch.setattr(module, "QdrantClient", FakeClient)

    results = module.retrieve_section_context(
        section_title="Warranty",
        company_id="company_1",
        cohere_key="cohere-key",
        qdrant_url="http://qdrant",
        qdrant_key="qdrant-key",
        top_k=1,
        min_score=0.0,
        max_results=4,
    )

    assert calls["api_key"] == "cohere-key"
    assert "Section: Warranty" in calls["query_text"]
    assert "Domain intent:" in calls["query_text"]
    assert calls["collections"] == ["tender_chunks", "company_knowledge"]
    assert len(results) == 2
    assert {"source", "text", "chunk_id", "doc_id", "page_start", "score"} <= set(results[0])


def test_retrieve_section_context_filters_low_scores(monkeypatch):
    from pipeline_one.retrieval import retrieve_context as module

    monkeypatch.setattr(module, "embed_query", lambda text, api_key: [0.1, 0.2])

    class FakeClient:
        def __init__(self, url: str, api_key: str):
            pass

        def query_points(self, collection_name, query, limit, query_filter):
            if collection_name == "tender_chunks":
                return SimpleNamespace(points=[_point("Low scoring tender chunk", 0.2)])
            return SimpleNamespace(points=[_point("High scoring company chunk", 0.8, "c_00003")])

    monkeypatch.setattr(module, "QdrantClient", FakeClient)

    results = module.retrieve_section_context(
        section_title="Performance Guarantee",
        company_id="company_1",
        cohere_key="cohere-key",
        qdrant_url="http://qdrant",
        qdrant_key="qdrant-key",
        min_score=0.5,
        max_results=4,
    )

    assert [item["text"] for item in results] == ["High scoring company chunk"]
