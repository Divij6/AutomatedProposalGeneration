from __future__ import annotations


def test_context_assembly_enforces_limits_and_suppresses_duplicates():
    from pipeline_one.retrieval.context_assembler import assemble_context_items

    repeated = "Warranty support includes replacement service and defect liability coverage."
    items = [
        {"source": "tender", "text": repeated, "score": 0.95, "chunk_id": "c_00001"},
        {"source": "tender", "text": repeated, "score": 0.94, "chunk_id": "c_00002"},
        {
            "source": "tender",
            "text": "Warranty support includes replacement services and defect liability coverage.",
            "score": 0.93,
            "chunk_id": "c_00003",
        },
        {
            "source": "company",
            "text": "Company service teams provide warranty response and maintenance support.",
            "score": 0.9,
            "chunk_id": "c_00004",
        },
        {
            "source": "company",
            "text": "This extra company paragraph should be trimmed by the chunk limit.",
            "score": 0.88,
            "chunk_id": "c_00005",
        },
    ]

    assembled = assemble_context_items(
        items,
        max_chunks=2,
        max_words=30,
        min_score=0.5,
        source_limits={"tender": 1, "company": 1},
    )

    assert len(assembled) == 2
    assert [item["source"] for item in assembled] == ["tender", "company"]
    assert sum(item["word_count"] for item in assembled) <= 30
    assert assembled[0]["chunk_id"] == "c_00001"


def test_context_assembly_applies_score_threshold_and_truncates_long_text():
    from pipeline_one.retrieval.context_assembler import assemble_context_items

    long_text = " ".join(f"word{i}" for i in range(120))
    items = [
        {"source": "tender", "text": "below threshold", "score": 0.1},
        {"source": "company", "text": long_text, "score": 0.9},
    ]

    assembled = assemble_context_items(
        items,
        max_chunks=3,
        max_words=50,
        min_score=0.5,
        source_limits={"company": 2},
    )

    assert len(assembled) == 1
    assert assembled[0]["source"] == "company"
    assert assembled[0]["context_truncated"] is True
    assert assembled[0]["word_count"] <= 51
