"""
Prompt builders for enterprise tender compliance generation.

These helpers keep prompt policy out of the LangGraph node while preserving the
existing node inputs and outputs. The strategy is clause-first: answer the tender
requirement, cite only retrieved support, and avoid brochure-style language.
"""

from __future__ import annotations

import re


BANNED_MARKETING_PHRASES = [
    "we are committed",
    "we possess extensive expertise",
    "we are pleased to",
    "cutting-edge",
    "world-class",
    "state-of-the-art",
    "industry-leading",
    "renowned",
    "highly skilled team",
    "trusted partner",
]


NEGATIVE_STYLE_POLICY = "\n".join(
    f'- Do not use "{phrase}".' for phrase in BANNED_MARKETING_PHRASES
)


FEW_SHOT_POLICY = """Style examples:
Bad: We are fully committed to delivering world-class fire protection solutions with cutting-edge technology.
Corrected: We confirm compliance with the specified fire protection system requirements including design, supply, installation, testing, and commissioning.

Bad: We possess extensive expertise in this area and are pleased to offer our trusted services.
Corrected: Our scope includes installation, testing, commissioning, and integration with the existing fire alarm network.

Bad: Our industry-leading team will provide state-of-the-art support throughout the project.
Corrected: Support will be provided only for the obligations stated in the tender and supported by the retrieved company evidence."""


def generation_length_policy(section_title: str, verbosity: str = "concise") -> dict:
    """Return paragraph/token limits for common tender clause types."""
    title = str(section_title or "").lower()
    verbosity = (verbosity or "concise").lower()

    policy = {"paragraphs": "1 paragraph", "max_tokens": 220, "max_words": 95}

    if any(marker in title for marker in ("warranty", "defect liability", "quantity variation")):
        policy = {"paragraphs": "1 paragraph", "max_tokens": 170, "max_words": 75}
    elif any(marker in title for marker in ("completion", "delivery", "timeline", "period")):
        policy = {"paragraphs": "maximum 2 short paragraphs", "max_tokens": 260, "max_words": 130}
    elif any(marker in title for marker in ("scope", "technical", "specification", "methodology")):
        policy = {"paragraphs": "2 to 3 short paragraphs", "max_tokens": 360, "max_words": 190}

    if verbosity == "standard":
        policy["max_tokens"] = int(policy["max_tokens"] * 1.25)
        policy["max_words"] = int(policy["max_words"] * 1.25)
    elif verbosity == "detailed":
        policy["max_tokens"] = int(policy["max_tokens"] * 1.6)
        policy["max_words"] = int(policy["max_words"] * 1.6)

    return policy


def build_form_field_prompt(company_name: str, field_label: str, company_context: str) -> str:
    return f"""You are completing a field in a formal tender response for {company_name}.

FIELD LABEL:
{field_label}

RETRIEVED COMPANY EVIDENCE:
{company_context}

Generation policy:
- Output only the field value.
- Use only retrieved company evidence.
- If the value is not present, write: No explicit supporting evidence was retrieved.
- Do not add labels, markdown, explanations, or marketing language.
{NEGATIVE_STYLE_POLICY}

Field value:"""


def build_table_prompt(
    company_name: str,
    requirement: str,
    tender_context: str,
    company_context: str,
) -> str:
    return f"""You are an EPC contractor's technical compliance engineer completing a tender compliance table for {company_name}.

TENDER REQUIREMENT / SPECIFICATION:
{requirement}

RELEVANT TENDER CLAUSE CONTEXT:
{tender_context}

RETRIEVED COMPANY EVIDENCE:
{company_context}

Task:
Fill the two response columns for this row. Output ONLY valid JSON.

Compliance writing policy:
- Start from the tender requirement, not from a company profile.
- State the offered scope or capability only when supported by retrieved company evidence.
- Confirm compliance only when the retrieved evidence supports it.
- If evidence is missing, write exactly: No explicit supporting evidence was retrieved.
- Do not invent certifications, standards, OEM approvals, project experience, ratings, materials, datasheets, or test certificates.
- Avoid brochure-style writing, exaggerated claims, and unsupported superiority claims.
{NEGATIVE_STYLE_POLICY}

{FEW_SHOT_POLICY}

JSON schema:
{{
  "specification_offered": "concise clause-specific response",
  "notes_remarks_ref": "retrieved evidence reference or No explicit supporting evidence was retrieved."
}}"""


def build_table_repair_prompt(requirement: str, company_context: str) -> str:
    return f"""Your previous tender compliance table answer was too vague or promotional.

REQUIREMENT:
{requirement}

RETRIEVED COMPANY EVIDENCE:
{company_context}

Rewrite both columns as concise procurement compliance text.

Rules:
- Use only the retrieved evidence above.
- If a fact is not evidenced, write: No explicit supporting evidence was retrieved.
- Do not invent certifications, standards, OEM approvals, datasheets, test certificates, or project experience.
- Do not use generic phrases such as compliant, as per tender, shall meet, or refer to documentation unless accompanied by specific retrieved evidence.
{NEGATIVE_STYLE_POLICY}

Output ONLY valid JSON:
{{
  "specification_offered": "concise clause-specific response",
  "notes_remarks_ref": "retrieved evidence reference or No explicit supporting evidence was retrieved."
}}"""


def build_paragraph_prompt(
    company_name: str,
    section_title: str,
    tender_context: str,
    company_context: str,
    verbosity: str = "concise",
) -> tuple[str, dict]:
    policy = generation_length_policy(section_title, verbosity)

    prompt = f"""You are an EPC contractor and technical compliance engineer drafting a procurement tender response for {company_name}.

SECTION / CLAUSE:
{section_title}

TENDER REQUIREMENT CONTEXT:
{tender_context}

RETRIEVED COMPANY EVIDENCE:
{company_context}

Write a concise enterprise tender compliance response.

Required structure:
1. Compliance confirmation against the tender clause.
2. Technical capability or scope supported by retrieved evidence.
3. Execution commitment only if relevant to the clause.
4. Warranty/support only if the clause is about warranty, defects, service, or support.

Length limit:
- {policy["paragraphs"]}.
- Maximum {policy["max_words"]} words.

Evidence and hallucination policy:
- Use only the retrieved tender context and company evidence.
- Do not invent certifications, standards, OEM approvals, project experience, datasheets, ratings, or test certificates.
- If company evidence is missing for a requested claim, write: No explicit supporting evidence was retrieved.
- Do not repeat company overview, NFPA statements, AMC/support text, or certifications unless directly relevant and retrieved.

Tone policy:
- Use procurement-style compliance wording.
- Prefer: "We confirm compliance..." or "Our scope includes..."
- Avoid brochure-style writing, exaggerated claims, and unsupported superiority claims.
{NEGATIVE_STYLE_POLICY}

{FEW_SHOT_POLICY}

Output rules:
- No markdown.
- Do not repeat the section title.
- Do not mention retrieved context or evidence as a process.
- Write only the proposal response text.

Proposal response:"""
    return prompt, policy


def build_style_repair_prompt(
    section_title: str,
    generated_text: str,
    max_words: int,
) -> str:
    return f"""Revise the following tender response to comply with enterprise procurement style.

SECTION / CLAUSE:
{section_title}

DRAFT RESPONSE:
{generated_text}

Revision rules:
- Maximum {max_words} words.
- Remove marketing language and unsupported superiority claims.
- Keep only clause-specific compliance, supported capability, and relevant execution commitment.
- If support for a claim is not explicit in the draft, replace it with: No explicit supporting evidence was retrieved.
{NEGATIVE_STYLE_POLICY}

Return only the revised response. No markdown."""


def contains_banned_marketing(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(phrase in lowered for phrase in BANNED_MARKETING_PHRASES)


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", str(text or "")))
