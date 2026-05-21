from __future__ import annotations


def test_insufficient_knowledge_fallback_does_not_claim_unseen_documents():
    from agents.nodes.generate_section_node import _insufficient_knowledge_output

    offered, notes = _insufficient_knowledge_output("Warranty")
    combined = f"{offered} {notes}".lower()

    assert "datasheet" not in combined
    assert "certificate" not in combined
    assert "test certificate" not in combined
    assert "no explicit supporting evidence was retrieved" in combined


def test_paragraph_prompt_uses_compliance_policy_and_bans_marketing_terms():
    from agents.prompt_builders import build_paragraph_prompt

    prompt, policy = build_paragraph_prompt(
        company_name="Acme Fire",
        section_title="Warranty",
        tender_context="Warranty period shall be provided.",
        company_context="No company knowledge found.",
        verbosity="concise",
    )

    lowered = prompt.lower()
    assert "technical compliance engineer" in lowered
    assert "world-class" in lowered
    assert "do not use" in lowered
    assert "no explicit supporting evidence was retrieved" in lowered
    assert "bad:" in lowered
    assert "corrected:" in lowered
    assert policy["max_words"] <= 75


def test_style_policy_detects_banned_marketing_language():
    from agents.prompt_builders import contains_banned_marketing

    assert contains_banned_marketing("We are committed to world-class service.")
    assert not contains_banned_marketing("We confirm compliance with the tender clause.")
