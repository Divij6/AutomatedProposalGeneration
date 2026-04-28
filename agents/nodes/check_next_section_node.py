"""
check_next_section_node.py — unchanged logic, cleaner code.
"""


def check_next_section_node(state: dict) -> str:

    index = state["section_index"]
    total = len(state["proposal_sections"])

    print(f"  [CHECK] section {index}/{total}")

    if index < total:
        return "process_section"
    else:
        print("\nAll sections processed — compiling\n")
        return "end"