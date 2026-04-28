# # =============================================================
# # PROVIDER OPTIONS (only one block should be active at a time)
# # =============================================================
#
# # -----------------------------------------------------------------
# # OPTION 1 — NVIDIA API (Nemotron) ← ACTIVE
# # -----------------------------------------------------------------
# # from openai import OpenAI
# # from config import NVIDIA_API_KEY
# #
# # client = OpenAI(
# #     base_url="https://integrate.api.nvidia.com/v1",
# #     api_key=NVIDIA_API_KEY
# # )
# #
# # NVIDIA_MODEL = "nvidia/llama-3.1-nemotron-70b-instruct"
#
#
# # -----------------------------------------------------------------
# # OPTION 2 — OLLAMA (local) ← commented out
# # To switch: comment out OPTION 1 block above and uncomment below
# # -----------------------------------------------------------------
# from openai import OpenAI   # Ollama exposes an OpenAI-compatible endpoint
#
# client = OpenAI(
#     base_url="http://localhost:11434/v1",
#     api_key="ollama"          # Ollama ignores the key but the param is required
# )
#
# OLLAMA_MODEL = "gemma4:e4b"     # name of the model you pulled with `ollama pull`
# # -----------------------------------------------------------------
#
# # -----------------------------------------------------------------
# # OPTION 3 — GROQ (original, kept for reference)
# # -----------------------------------------------------------------
# # from groq import Groq
# # from config import GROQ_API_KEY
# # client = Groq(api_key=GROQ_API_KEY)
# # GROQ_MODEL = "llama-3.1-8b-instant"
# # -----------------------------------------------------------------
#
#
# def _call_llm(prompt: str, max_tokens: int = 5, temperature: float = 0) -> str:
#     """
#     Single place to swap providers.
#     Change the model string and/or client above — this function stays the same.
#     """
#
#     # ── NVIDIA / Ollama (OpenAI-compatible) ──────────────────────
#     response = client.chat.completions.create(
#         model=OLLAMA_MODEL,  # swap to OLLAMA_MODEL when using Ollama
#         messages=[{"role": "user", "content": prompt}],
#         temperature=temperature,
#         max_tokens=max_tokens,
#     )
#     return response.choices[0].message.content
#
#     # ── Groq (uncomment if switching back) ───────────────────────
#     # response = client.chat.completions.create(
#     #     model=GROQ_MODEL,
#     #     messages=[{"role": "user", "content": prompt}],
#     #     temperature=temperature,
#     #     max_tokens=max_tokens,
#     # )
#     # return response.choices[0].message.content
#
#
# def validate_section_node(state):
#     section = state["current_section"]
#
#     title = section["title"]
#
#     print(f"Validating section: {title}")
#
#     prompt = f"""
#
#     You are analyzing tender proposal sections.
#
#     Decide whether this section needs content generation.
#
#     Return ONLY one word:
#
#     GENERATE
#     or
#     SKIP
#
#     SECTION TITLE:
#
#     {title}
#
#     """
#
#     # Clean output
#     decision = (
#         _call_llm(prompt=prompt, max_tokens=5, temperature=0)
#         .strip()
#         .upper()
#         .replace(".", "")
#     )
#
#     print(f"Decision: {decision}")
#
#     # IMPORTANT FIX — increment index on skip
#
#     if "SKIP" in decision:
#
#         state["skip_section"] = True
#
#         print(f"Skipping section: {title}")
#
#         # MOVE TO NEXT SECTION
#         state["section_index"] += 1
#
#     else:
#
#         state["skip_section"] = False
#
#     return state

"""
validate_section_node.py

Decides GENERATE or SKIP for each section.

Fix vs old version:
- For TABLE mode, almost every row should be generated unless it's
  completely empty or a sub-header row — the old validation was too
  aggressive and was skipping legitimate spec rows.
- In paragraph mode, keep existing logic but tighten the prompt.
"""

from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)
OLLAMA_MODEL = "gemma4:e2b"


def _call_llm(prompt: str, max_tokens: int = 5, temperature: float = 0) -> str:
    response = client.chat.completions.create(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def _is_empty_or_header_row(title: str) -> bool:
    """
    Quick heuristic: if the title is very short, all-caps header-like,
    or contains only punctuation/numbers — skip it.
    """
    t = title.strip()
    if not t:
        return True
    if len(t) <= 3:
        return True
    # Looks like a column header (Sr No, S.No, #, etc.)
    if t.lower() in {"sr no", "s.no", "no.", "#", "sr.", "item", "item no"}:
        return True
    return False


def validate_section_node(state: dict) -> dict:
    section = state["current_section"]
    title = section["title"]
    mode = state.get("mode", "paragraph")

    print(f"  [VALIDATE] {title}")

    # ── TABLE MODE: only skip empty/header rows ───────────────────
    if mode == "table":
        if _is_empty_or_header_row(title):
            state["skip_section"] = True
            state["section_index"] += 1
            print(f"  → SKIP (empty/header row)")
        else:
            state["skip_section"] = False
            print(f"  → GENERATE")
        return state

    # ── PARAGRAPH MODE: use LLM to decide ────────────────────────
    prompt = f"""You are reviewing a tender proposal section title.

Decide if this section needs AI-generated content, or should be skipped
(e.g. it is a cover page label, table of contents entry, page number, 
signature block, or purely administrative field with no substantive content).

Section title: "{title}"

Reply with exactly one word:
GENERATE  ← if this section needs written proposal content
SKIP      ← if this is administrative/structural with no content needed"""

    decision = (
        _call_llm(prompt=prompt, max_tokens=5, temperature=0)
        .strip()
        .upper()
        .replace(".", "")
        .split()[0]  # take only first word
    )

    print(f"  → {decision}")

    if "SKIP" in decision:
        state["skip_section"] = True
        state["section_index"] += 1
    else:
        state["skip_section"] = False

    return state