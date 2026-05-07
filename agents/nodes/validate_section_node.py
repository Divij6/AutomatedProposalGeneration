"""
validate_section_node.py

Changes:
- Uses Groq as primary LLM, Ollama gemma4:e2b as fallback.
- In TABLE mode: only skip truly empty rows or column-header rows.
- In PARAGRAPH mode: tighter prompt, defaults to GENERATE on any ambiguity.
"""

import logging

from groq import Groq
from openai import OpenAI

from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

# ── Groq (primary) ─────────────────────────────────────────────────────────
groq_client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Ollama (fallback) ──────────────────────────────────────────────────────
ollama_client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
OLLAMA_MODEL = "gemma4:e2b"


def _call_llm(prompt: str, max_tokens: int = 5, temperature: float = 0) -> str:
    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content or ""
        if content.strip():
            return content
    except Exception as e:
        logger.warning("Groq validate call failed (%s); falling back to Ollama", e)

    try:
        response = ollama_client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choices = getattr(response, "choices", None) or []
        if choices:
            return getattr(choices[0].message, "content", "") or ""
    except Exception as e2:
        logger.warning("Ollama validate fallback failed: %s", e2)

    return ""


def _is_empty_or_header_row(title: str) -> bool:
    t = title.strip()
    if not t:
        return True
    if len(t) <= 3:
        return True
    if t.lower() in {
        "sr no", "s.no", "no.", "#", "sr.", "item", "item no",
        "sl no", "sl. no", "s. no", "serial no", "serial number",
        "description", "unit", "qty", "quantity", "uom",
    }:
        return True
    # purely numeric
    if t.replace(".", "").replace(",", "").isdigit():
        return True
    return False


def validate_section_node(state: dict) -> dict:
    section = state.get("current_section") or {}
    title = section.get("title", "").strip()
    mode = state.get("mode", "paragraph")

    if not title:
        index = state.get("section_index", 0)
        logger.warning("Missing title; skipping section at index %s", index)
        state["skip_section"] = True
        state["section_index"] = index + 1
        return state

    logger.info("[VALIDATE] %s", title)

    # ── TABLE MODE ─────────────────────────────────────────────────────────
    if mode == "table":
        if _is_empty_or_header_row(title):
            state["skip_section"] = True
            state["section_index"] += 1
            logger.info("Validation: SKIP (header/empty row)")
        else:
            state["skip_section"] = False
            logger.info("Validation: GENERATE")
        return state

    # ── PARAGRAPH MODE ─────────────────────────────────────────────────────
    prompt = f"""Is this a content section in a tender proposal that needs written response?
Reply with exactly one word: GENERATE or SKIP.

SKIP only if it is: a page number, a signature block, a table of contents entry, a blank placeholder, or a purely administrative label with no content to write.
GENERATE for everything else including scope, technical, commercial, warranty, experience, eligibility sections.

Section title: "{title}"

Answer:"""

    raw = (
        _call_llm(prompt=prompt, max_tokens=5, temperature=0)
        .strip().upper().replace(".", "").split()
    )
    decision = raw[0] if raw else "GENERATE"

    if not raw:
        logger.warning("Empty validation decision; defaulting to GENERATE")

    logger.info("Validation decision: %s", decision)

    if "SKIP" in decision:
        state["skip_section"] = True
        state["section_index"] += 1
    else:
        state["skip_section"] = False

    return state