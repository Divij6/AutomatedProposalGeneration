from pipeline_one.retrieval.retrieve_context import retrieve_section_context
import os

from dotenv import load_dotenv

load_dotenv()

COHERE_KEY = os.getenv("COHERE_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_KEY = os.getenv("QDRANT_KEY")



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
