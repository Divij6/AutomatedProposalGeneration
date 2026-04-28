from pipeline_one.retrieval.retrieve_context import retrieve_section_context

COHERE_KEY = "prRZFhvcguOv8Ss4svLYWN8kGCGYypdF5hh3pXZV"
QDRANT_URL = "https://e1a408b9-18aa-46f7-a3f7-fcfbebb20345.sa-east-1-0.aws.cloud.qdrant.io:6333"
QDRANT_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.mlaWJmy3OGwF-p29vJjWB-3OmJLXkoSPCsvPDw4d1Eo"



company_id = "65760466-9a51-46f2-a408-f644d42bc7dd"


context = retrieve_section_context(

    section_title="Scope of Work",

    company_id=company_id,

    cohere_key=COHERE_KEY,

    qdrant_url=QDRANT_URL,

    qdrant_key=QDRANT_KEY,

    top_k=3

)


print("\nRetrieved Context:\n")

for c in context:

    print(
        c["source"],
        "→",
        c["text"][:200],
        "\n"
    )