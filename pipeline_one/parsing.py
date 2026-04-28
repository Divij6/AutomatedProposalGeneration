import json
import re
from pathlib import Path
from parsing.pipeline import run_parsing_pipeline

# ── Put your tender PDF path here ─────────────────────────────────────────────
PDF_PATH = r"D:\Third Year\Projects\DataExtraction\documents\GeM-Bidding-8887545.pdf"

# ── Run the pipeline ──────────────────────────────────────────────────────────
result = run_parsing_pipeline(PDF_PATH)

# ── Print summary ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("PHASE 1 RESULT SUMMARY")
print("=" * 60)
print(f"doc_id         : {result.doc_id}")
print(f"file_name      : {result.file_name}")
print(f"total_pages    : {result.total_pages}")
print(f"parser_used    : {result.parser_used.value}")
print(f"language       : {result.language_hint}")
print(f"top sections   : {len(result.sections)}")
print(f"total tables   : {len(result.all_tables)}")
print(f"parse_time     : {result.metadata.get('parse_time_seconds')}s")
print(f"total_time     : {result.metadata.get('total_pipeline_time_seconds')}s")



# ── First 3 sections preview ──────────────────────────────────────────────────
print("\n" + "─" * 60)
print("FIRST 3 SECTIONS PREVIEW")
print("─" * 60)
for section in result.sections[:3]:
    print(f"\n[Level {section.level}] {section.title}")
    print(f"  Pages      : {section.page_start} → {section.page_end}")
    print(f"  Content    : {section.content[:200]}...")
    print(f"  Tables     : {len(section.tables)}")
    print(f"  Children   : {len(section.children)}")

# ── First 2 tables preview ────────────────────────────────────────────────────
if result.all_tables:
    print("\n" + "─" * 60)
    print("FIRST 2 TABLES PREVIEW")
    print("─" * 60)
    for table in result.all_tables[:2]:
        print(f"\n[{table.table_id}] Page {table.page_number} | Section: {table.section_title}")
        print(f"  Headers : {table.headers}")
        print(f"  Rows    : {len(table.rows)} rows")
        print(f"  Markdown preview:")
        print("  " + table.raw_markdown[:300].replace("\n", "\n  "))


# ═════════════════════════════════════════════════════════════════════════════
# SAVE OUTPUT
# ═════════════════════════════════════════════════════════════════════════════

def save_as_json(result, output_path: str):
    """
    Saves the full ParsedDocument as a JSON file.
    Every section, table, quality report and metadata is included.
    Good for inspecting the exact data structure and debugging.
    """

    def section_to_dict(s):
        return {
            "section_id" : s.section_id,
            "title"      : s.title,
            "level"      : s.level,
            "page_start" : s.page_start,
            "page_end"   : s.page_end,
            "content"    : s.content,
            "tables"     : [
                {
                    "table_id"     : t.table_id,
                    "page_number"  : t.page_number,
                    "section_title": t.section_title,
                    "headers"      : t.headers,
                    "rows"         : t.rows,
                    "raw_markdown" : t.raw_markdown,
                }
                for t in s.tables
            ],
            "children"   : [section_to_dict(c) for c in s.children],
        }

    output = {
        "doc_id"       : result.doc_id,
        "file_name"    : result.file_name,
        "total_pages"  : result.total_pages,
        "parser_used"  : result.parser_used.value,
        "language_hint": result.language_hint,
        "metadata" : result.metadata,
        "sections" : [section_to_dict(s) for s in result.sections],
        "all_tables": [
            {
                "table_id"     : t.table_id,
                "page_number"  : t.page_number,
                "section_title": t.section_title,
                "headers"      : t.headers,
                "rows"         : t.rows,
                "raw_markdown" : t.raw_markdown,
            }
            for t in result.all_tables
        ],
    }

    Path(output_path).write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\n✓ JSON saved → {output_path}")


def save_as_markdown(result, output_path: str):
    """
    Saves the parsed document as a clean readable Markdown file.
    Sections become headings, tables render as markdown tables.
    Good for visually verifying that parsing captured the right content.
    """

    def render_section(s, depth=1):
        lines = []
        heading = "#" * depth + " " + s.title
        lines.append(heading)
        lines.append(f"*Pages {s.page_start}–{s.page_end}*\n")

        if s.content.strip():
            lines.append(s.content.strip())
            lines.append("")

        for table in s.tables:
            lines.append(f"\n**Table: {table.table_id} (page {table.page_number})**\n")
            lines.append(table.raw_markdown)
            lines.append("")

        for child in s.children:
            lines.extend(render_section(child, depth=depth + 1))

        return lines

    lines = [
        f"# {result.file_name}",
        f"",
        f"| Field | Value |",
        f"|---|---|",
        f"| doc_id | {result.doc_id} |",
        f"| total_pages | {result.total_pages} |",
        f"| parser_used | {result.parser_used.value} |",
        f"| language | {result.language_hint} |",
        f"| sections | {len(result.sections)} |",
        f"| tables | {len(result.all_tables)} |",
        f"",
        f"---",
        f"",
    ]

    for section in result.sections:
        lines.extend(render_section(section, depth=2))
        lines.append("---")
        lines.append("")

    Path(output_path).write_text(
        "\n".join(lines),
        encoding="utf-8"
    )
    print(f"✓ Markdown saved → {output_path}")


# ── Save both files next to the PDF ───────────────────────────────────────────
output_dir  = Path(PDF_PATH).parent
output_stem = Path(PDF_PATH).stem

save_as_json(result,     str(output_dir / f"{output_stem}_parsed.json"))
save_as_markdown(result, str(output_dir / f"{output_stem}_parsed.md"))