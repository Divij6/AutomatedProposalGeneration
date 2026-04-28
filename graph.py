import json

from agents.graph import build_graph


# Load saved API response
with open(
    "response_1776237335634.json"
) as f:

    data = json.load(f)


proposal_json = data[
    "proposal_json"
]


graph = build_graph()


initial_state = {

    "company_id":
        "65760466-9a51-46f2-a408-f644d42bc7dd",

    "doc_id":
        data["doc_id"],

    "proposal_json":
        proposal_json,

    "proposal_sections": [],

    "generated_sections": [],

    "current_section": {},

    "context": [],
    "section_index" :0,

    "status": "starting"

}


result = graph.invoke(initial_state)

print("\nFinal State:\n")

print(
    "Sections loaded:",
    len(result["proposal_sections"])
)

print(
    "Generated sections:",
    len(result["generated_sections"])
)

print("\n==============================")
print("GENERATED CONTENT")
print("==============================\n")

for section in result["generated_sections"]:

    print("\n------------------------------")

    print(
        "SECTION:",
        section["title"]
    )

    print("------------------------------")

    print(
        section["content"]
    )

    print("\n")